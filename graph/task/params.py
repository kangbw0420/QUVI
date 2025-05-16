import json
import re
from typing import Tuple, Dict
from datetime import datetime

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from graph.models import qwen_llm
from graph.prompts.prompts_api import PROMPT_PARAMS
from utils.retriever import retriever
from llm_admin.qna_manager import QnAManager
from utils.logger import setup_logger


qna_manager = QnAManager()
logger = setup_logger('params')

SQL_TEMPLATE = """SELECT * FROM sql_func('use_intt_id', 'user_id', 'company_id', 'from_date', 'to_date')"""

WEEKDAYS = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}

def convert_date_format(date_str: str) -> str:
    # 먼저 공백 제거
    date_str = date_str.strip()

    if len(date_str) == 8 and date_str.isdigit():
        return date_str
    # YYYY-MM-DD 형식 검사 및 변환
    elif len(date_str) == 10 and date_str[4] == "-" and date_str[7] == "-":
        return date_str.replace("-", "")
    return date_str

async def parameters(
        trace_id: str,
        selected_api: str,
        user_question: str,
        company_id: str,
        user_info: Tuple[str, str],
        flags: Dict = None
) -> Tuple[str, Tuple[str, str]]:
    """분석된 질문으로부터 SQL 쿼리를 생성
    Args:
        trace_id: 추적 ID
        selected_api: 선택된 API 함수명
        user_question: 사용자 질문
        company_id: 회사 ID
        user_info: 사용자 정보 튜플 (user_id, use_intt_id)
        flags: 상태 플래그 딕셔너리 (옵션)
        
    Returns:
        Tuple[str, Tuple[str, str]]: 
            - 생성된 SQL 쿼리문
            - (from_date, to_date) 형식의 날짜 범위 튜플
    """
    logger.info(f"Generating parameters for API '{selected_api}', question: '{user_question[:50]}...'")
    user_id, use_intt_id = user_info
    
    # flags가 None이면 빈 딕셔너리로 초기화
    if flags is None:
        flags = {}

    try:
        json_format = '"from_date": from_date, "to_date": to_date'
        
        today = datetime.now()
        prompt_today = today.strftime("%Y년 %m월 %d일")
        today_str = today.strftime("%Y%m%d")
        logger.info(f"Current date: {prompt_today} ({today_str})")

        system_prompt = PROMPT_PARAMS.format(today=prompt_today, json_format=json_format)

        few_shots = await retriever.get_few_shots(
            query_text=user_question, collection_name="shots_params_creator", top_k=5
        )
        few_shot_prompt = []
        for example in reversed(few_shots):
            if "date" in example:
                human_with_date = f'{example["input"]}, 오늘: {example["date"]}.'
            else:
                human_with_date = example["input"]
            formatted_output = "{" + str(example["output"]) + "}"
            few_shot_prompt.append(("human", human_with_date))
            few_shot_prompt.append(("ai", formatted_output))

        formatted_today = today_str
        weekday = WEEKDAYS[today.weekday()]

        formatted_question = f"{user_question}, 오늘: {formatted_today} {weekday}요일."

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_prompt),
                *few_shot_prompt,
                ("human", formatted_question),
            ]
        )

        logger.debug("===== params(Q) =====")
        qna_id = qna_manager.create_question(
            trace_id=trace_id, question=prompt, model="qwen_nl2sql"
        )

        chain = prompt | qwen_llm
        raw_output = chain.invoke({"user_question": user_question})

        # JSON 형식이 없을 경우의 에러 처리
        try:
            # 먼저 JsonOutputParser로 시도
            json_parser = JsonOutputParser()
            output = json_parser.parse(raw_output)
        except Exception as json_error:
            # JSON 파싱에 실패한 경우, 텍스트에서 JSON 형식 찾기 시도
            json_pattern = re.search(r'\{.*?\}', raw_output, re.DOTALL)
            if json_pattern:
                try:
                    json_str = json_pattern.group(0)
                    output = json.loads(json_str)
                except:
                    # JSON 형식으로 보이는 패턴이 있지만 파싱 실패
                    raise ValueError(f"JSON이 있는 거 같은데 파싱이 어려워요..: {raw_output}")
            else:
                # JSON 형식이 전혀 없음
                raise ValueError(f"JSON이 없어요..: {raw_output}")

        # 필수 키 확인
        if "from_date" not in output or "to_date" not in output:
            raise ValueError(f"응답에 (from_date, to_date)가 없어요..: {output}")

        logger.info(f"Extracted parameters: from_date={output.get('from_date')}, to_date={output.get('to_date')}")

        # from_date와 to_date 형식 변환
        from_date = convert_date_format(output["from_date"])
        to_date = convert_date_format(output["to_date"])
        
        # 미래 날짜 교정: api는 sql 로직과 달리 교정할 날짜 부분이 명확하므로(sql을 view_date에서 복잡하게 처리) 따로 간단히 처리
        if from_date > today_str:
            logger.warning(f"Future from_date: {from_date}, correcting to today: {today_str}")
            from_date = today_str
            flags["future_date"] = True
            
        if to_date > today_str:
            logger.warning(f"Future to_date: {to_date}, correcting to today: {today_str}")
            to_date = today_str
            flags["future_date"] = True

        logger.info(f"Final parameters: from_date={from_date}, to_date={to_date}")
        
        # 출력에서 SQL 쿼리 조합
        sql_query = (
            SQL_TEMPLATE.replace("sql_func", selected_api)
            .replace("use_intt_id", use_intt_id)
            .replace("user_id", user_id)
            .replace("company_id", company_id)
            .replace("from_date", from_date)
            .replace("to_date", to_date)
        )

        logger.debug("===== params(A) =====")
        logger.info(f"Generated SQL query: {sql_query}")
        output_str = json.dumps(output, ensure_ascii=False)
        qna_manager.record_answer(qna_id, output_str)

        date_info = (from_date, to_date)

        return sql_query.strip(), date_info

    except Exception as e:
        logger.error(f"Error generating parameters: {str(e)}")
        raise