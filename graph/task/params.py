import json
import re
from typing import Tuple, Dict

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from graph.models import qwen_llm
from graph.prompts.prompts_api import PROMPT_PARAMS
from utils.common.llm_output_handler import handle_ai_colon
from utils.retriever import retriever
from llm_admin.qna_manager import QnAManager
from utils.logger import setup_logger
from utils.common.chat_history import convert_to_chat_history
from utils.common.date_utils import (
    get_today_formatted,
    get_today_str,
    format_date_with_weekday,
    convert_date_format,
    is_future_date
)

qna_manager = QnAManager()
logger = setup_logger('params')

# SQL_TEMPLATE = """SELECT * FROM sql_func('use_intt_id', 'user_id', 'company_id', 'from_date', 'to_date')"""
SQL_TEMPLATE = """SELECT * FROM sql_func('first_param', 'second_param', 'third_param', 'from_date', 'to_date')"""


async def parameters(
    trace_id: str,
    selected_api: str,
    user_question: str,
    company_id: str,
    user_info: Dict[str, str],
    flags: Dict = None,
    params_history: dict = {},
) -> Tuple[str, Tuple[str, str]]:
    """분석된 질문으로부터 SQL 쿼리를 생성
    Args:
        trace_id: 추적 ID
        selected_api: 선택된 API 함수명
        user_question: 사용자 질문
        company_id: 회사 ID
        user_info: 사용자 정보 딕셔너리 (user_id, use_intt_id, intt_biz_no, intt_cntrct_id)
        flags: 상태 플래그 딕셔너리 (옵션)
        params_history: chain_id별로 그룹화된 과거 대화 이력

    Returns:
        Tuple[str, Tuple[str, str]]:
            - 생성된 SQL 쿼리문
            - (from_date, to_date) 형식의 날짜 범위 튜플
    """
    logger.info(
        f"Generating parameters for API '{selected_api}', question: '{user_question[:50]}...'")
    user_id, use_intt_id = user_info
    try:
        json_format = '"from_date": from_date, "to_date": to_date'

        prompt_today = get_today_formatted()
        today_str = get_today_str()

        system_prompt = PROMPT_PARAMS.format(
            today=prompt_today, json_format=json_format)

        few_shots, retrieve_time = await retriever.get_few_shots(
            query_text=user_question, collection_name="shots_params_creator", top_k=5
        )

        qna_id = qna_manager.create_qna_id(trace_id)

        few_shot_prompt = []
        for order, example in enumerate(reversed(few_shots), 1):
            if "date" in example:
                human_with_date = f'{example["input"]}, 오늘: {example["date"]}.'
            else:
                human_with_date = example["input"]
            formatted_output = "{" + str(example["output"]) + "}"
            few_shot_prompt.append(("human", human_with_date))
            few_shot_prompt.append(("ai", formatted_output))

            qna_manager.record_fewshot(
                qna_id=qna_id,
                retrieved=example["input"],
                human=human_with_date,
                ai=formatted_output,
                order=order
            )

        # 시스템 메시지와 퓨샷 합치기
        flattend_few_shot_prompt = "\n".join(
            f"{role}: {text}" for role, text in few_shot_prompt
        )
        concat_few_shot_prompt = f"{system_prompt}\n{flattend_few_shot_prompt}"

        # 사용자의 질문 포맷팅
        formatted_question = f"{user_question}, 오늘: {format_date_with_weekday()}."

        chat_history_prompt = convert_to_chat_history(
            params_history,
            required_fields=["user_question", "date_info"],
            human_field="user_question",
            ai_field="date_info"
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=concat_few_shot_prompt),
                *chat_history_prompt,
                ("human", formatted_question),
            ]
        )

        logger.info("===== params(Q) =====")
        qna_manager.update_question(
            qna_id=qna_id,
            question=prompt,
            model="qwen_nl2sql"
        )

        chain = prompt | qwen_llm
        raw_output = chain.invoke({"user_question": user_question})
        raw_output = handle_ai_colon(raw_output)

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
                    raise ValueError(
                        f"JSON이 있는 거 같은데 파싱이 어려워요..: {raw_output}")
            else:
                # JSON 형식이 전혀 없음
                raise ValueError(f"JSON이 없어요..: {raw_output}")

        # 필수 키 확인
        if "from_date" not in output or "to_date" not in output:
            raise ValueError(f"응답에 (from_date, to_date)가 없어요..: {output}")

        logger.info(
            f"Extracted parameters: from_date={output.get('from_date')}, to_date={output.get('to_date')}")

        # from_date와 to_date 형식 변환
        from_date = convert_date_format(output["from_date"])
        to_date = convert_date_format(output["to_date"])

        # 미래 날짜 교정
        if is_future_date(from_date):
            logger.warning(
                f"Future from_date: {from_date}, correcting to today: {today_str}")
            from_date = today_str
            flags["future_date"] = True

        if is_future_date(to_date):
            logger.warning(
                f"Future to_date: {to_date}, correcting to today: {today_str}")
            to_date = today_str
            flags["future_date"] = True

        logger.info(
            f"Final parameters: from_date={from_date}, to_date={to_date}")

        # 출력에서 SQL 쿼리 조합
        sql_query = (
            SQL_TEMPLATE.replace("sql_func", selected_api)
            .replace("first_param", use_intt_id)
            .replace("second_param", user_id)
            .replace("third_param", company_id)
            .replace("from_date", from_date)
            .replace("to_date", to_date)
        )

        logger.info("===== params(A) =====")
        logger.info(f"Generated SQL query: {sql_query}")
        output_str = json.dumps(output, ensure_ascii=False)
        qna_manager.record_answer(qna_id, output_str, retrieve_time)

        date_info = (from_date, to_date)

        return sql_query.strip(), date_info

    except Exception as e:
        logger.error(f"Error generating parameters: {str(e)}")
        raise
