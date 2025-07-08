from typing import Tuple

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from utils.common.llm_output_handler import handle_ai_colon, handle_sql_code_block
from graph.models import nl2sql
# from graph.prompts.prompts_core import PROMPT_NL2SQL
from graph.prompts.prompts_core import PROMPT_NL2SQL_AMT, PROMPT_NL2SQL_TRSC, PROMPT_NL2SQL_STOCK, PROMPT_NL2SQL_CARD_INFO, PROMPT_NL2SQL_CARD_TRSC
from utils.retriever import retriever
from llm_admin.qna_manager import QnAManager
from utils.logger import setup_logger
from utils.common.chat_history import convert_to_chat_history
from utils.common.date_utils import (
    get_today_formatted,
    format_date_with_weekday
)

qna_manager = QnAManager()
logger = setup_logger("nl2sql")

# 테이블별 프롬프트 매핑
PROMPT_MAPPING = {
    "amt": PROMPT_NL2SQL_AMT,
    "trsc": PROMPT_NL2SQL_TRSC,
    "stock": PROMPT_NL2SQL_STOCK,
    "card_info": PROMPT_NL2SQL_CARD_INFO,
    "card_trsc": PROMPT_NL2SQL_CARD_TRSC,
}

async def create_sql(
    trace_id: str,
    company_id: str,
    user_question: str,
    selected_table: str,
    date_info: Tuple[str, str],
    nl2sql_history: dict,
) -> str:
    """분석된 질문으로부터 SQL 쿼리를 생성
    Returns:
        str: 생성된 SQL 쿼리문
    Raises:
        ValueError: SQL 쿼리를 생성할 수 없거나, 추출 패턴이 매치되지 않는 경우
        TypeError: LLM 응답이 예상된 형식이 아닌 경우.
    """
    try:
        prompt_today = get_today_formatted()
        logger.info(f"nl2sql prompt_today: {prompt_today}")
        date_info_str = f"({date_info[0]}, {date_info[1]})"

        # 테이블별 프롬프트 선택
        if selected_table not in PROMPT_MAPPING:
            raise ValueError(f"Unsupported table: {selected_table}. Supported tables: {list(PROMPT_MAPPING.keys())}")
        
        selected_prompt = PROMPT_MAPPING[selected_table]
        system_prompt = selected_prompt.format(
            today=prompt_today, main_com=company_id, date_info=date_info_str
        )
        
        # system_prompt = PROMPT_NL2SQL.format(
        #     today=prompt_today, main_com=company_id, date_info=date_info_str
        # )
        # few_shots, retrieve_time = await retriever.get_few_shots(
        #     query_text=user_question, collection_name="shots_nl2sql", top_k=3
        # )
        # 테이블별로 shots_테이블명 컬렉션에서 퓨샷을 가져오도록 수정
        few_shot_collection = f"shots_{selected_table}"
        few_shots, retrieve_time = await retriever.get_few_shots(
            query_text=user_question, collection_name=few_shot_collection, top_k=3
        )

        qna_id = qna_manager.create_qna_id(trace_id)

        few_shot_prompt = []
        for order, example in enumerate(reversed(few_shots), 1):
            if "date" in example:
                human_with_date = f'{example["input"]}, 오늘: {example["date"]}.'
            else:
                human_with_date = example["input"]

            # Few-shot 예제 저장
            qna_manager.record_fewshot(
                qna_id=qna_id,
                retrieved=example["input"],
                human=human_with_date,
                ai=example["output"],
                order=order
            )

            few_shot_prompt.append(("human", human_with_date))
            few_shot_prompt.append(("ai", example["output"]))

        # 시스템 메시지와 퓨샷 합치기
        flattend_few_shot_prompt = "\n".join(
            f"{role}: {text}" for role, text in few_shot_prompt
        )
        concat_few_shot_prompt = f"{system_prompt}\n{flattend_few_shot_prompt}"

        # 사용자의 질문 포맷팅
        formatted_question = f"{user_question}, 오늘: {format_date_with_weekday()}."

        chat_history_prompt = convert_to_chat_history(
            nl2sql_history,
            required_fields=["user_question", "sql_query"],
            human_field="user_question",
            ai_field="sql_query",
            add_date_to_question=True
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=concat_few_shot_prompt),
                *chat_history_prompt,
                ("human", formatted_question),
            ]
        )

        logger.info("===== nl2sql(Q) =====")
        qna_manager.update_question(
            qna_id=qna_id,
            question=prompt,
            model="qwen_nl2sql"
        )

        chain = prompt | nl2sql
        output = chain.invoke(
            {"user_question": formatted_question, "main_com": company_id}
        )

        output = handle_ai_colon(output)
        # 출력에서 SQL 쿼리 추출
        sql_query = handle_sql_code_block(output)

        logger.info("===== nl2sql(A) =====")
        logger.info(f"Generated SQL query: {sql_query}")
        qna_manager.record_answer(qna_id, output, retrieve_time)

        return sql_query.strip()

    except Exception as e:
        logger.error(f"Error in create_sql: {str(e)}")
        raise
