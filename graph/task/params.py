import json
import re
from typing import Tuple
from datetime import datetime, timedelta

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from database.database_service import DatabaseService
from graph.models import qwen_llm
from utils.retriever import retriever

from llm_admin.qna_manager import QnAManager

database_service = DatabaseService()
qna_manager = QnAManager()

SQL_TEMPLATE = """SELECT * FROM sql_func('use_intt_id', 'user_id', 'main_com', 'from_date', 'to_date')"""

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
    main_com: str,
    user_info: Tuple[str, str],
    today: str,
    # yogeumjae: str,
    # flags: dict
) -> Tuple[str, Tuple[str, str]]:
    """분석된 질문으로부터 SQL 쿼리를 생성
    Returns:
        str: 생성된 SQL 쿼리문
    Raises:
        ValueError: SQL 쿼리를 생성할 수 없거나, 추출 패턴이 매치되지 않는 경우
        TypeError: LLM 응답이 예상된 형식이 아닌 경우.
    """
    user_id, use_intt_id = user_info

    try:
        json_format = '"from_date": from_date, "to_date": to_date'
        
        system_prompt = database_service.get_prompt(
            node_nm="params", prompt_nm="system"
        )[0]["prompt"].format(today=today, json_format=json_format)

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

        formatted_today = today.strftime("%Y%m%d")
        weekday = WEEKDAYS[today.weekday()]

        formatted_question = f"{user_question}, 오늘: {formatted_today} {weekday}요일."

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_prompt),
                *few_shot_prompt,
                ("human", formatted_question),
            ]
        )

        print("=" * 40 + "params(Q)" + "=" * 40)
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

        print(output)

        # from_date와 to_date 형식 변환
        from_date = convert_date_format(output["from_date"])
        to_date = convert_date_format(output["to_date"])

        # if yogeumjae == 'muryo':
        #     # 날짜 문자열을 datetime 객체로 변환
        #     from_date_dt = datetime.strptime(from_date, "%Y%m%d")
        #     today_dt = datetime.now().strptime(today, "%Y-%m-%d")
            
        #     # 날짜 차이 계산 (today - from_date)
        #     date_diff = today_dt - from_date_dt
            
        #     # from_date가 오늘보다 2일 이상 이전인 경우
        #     if date_diff.days >= 2:
        #         # 어제 날짜 계산
        #         yesterday = today_dt - timedelta(days=1)
        #         # 날짜 형식을 YYYYMMDD로 변환
        #         from_date = yesterday.strftime("%Y%m%d")
        #         # past_date 플래그를 True로 설정
        #         flags["past_date"] = True

        # 출력에서 SQL 쿼리 조합
        sql_query = (
            SQL_TEMPLATE.replace("sql_func", selected_api)
            .replace("use_intt_id", use_intt_id)
            .replace("user_id", user_id)
            .replace("main_com", main_com)
            .replace("from_date", from_date)
            .replace("to_date", to_date)
        )

        print("=" * 40 + "params(A)" + "=" * 40)
        print(sql_query)
        output_str = json.dumps(output, ensure_ascii=False)
        qna_manager.record_answer(qna_id, output_str)
        
        date_info = (from_date, to_date)

        return sql_query.strip(), date_info

    except Exception as e:
        raise
