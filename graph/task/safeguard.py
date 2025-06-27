from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from graph.models import qwen_llm as llm
from graph.prompts.prompts_core import PROMPT_NL2SQL
from graph.prompts.prompts_guardian import PROMPT_SAFEGUARD
from llm_admin.qna_manager import QnAManager
from utils.common.llm_output_handler import handle_sql_code_block
from utils.logger import setup_logger
from utils.common.date_utils import get_today_formatted


qna_manager = QnAManager()
logger = setup_logger("safeguard")


async def guard_query(
    trace_id: str,
    unsafe_query: str,
    user_question: str,
    flags: dict,
    sql_error: str = "",
) -> str:
    """에러가 발생했거나 날짜가 틀릴 수 있는 쿼리를 체크
    Returns:
        수정된 쿼리(문제 없으면 쿼리 그대로 return)
    """
    prompt_today = get_today_formatted()

    if flags["query_error"]:
        system_prompt = PROMPT_SAFEGUARD.format(
            user_question=user_question,
            today=prompt_today,
            unsafe_query=unsafe_query,
            sql_error=sql_error,
        )
    else:
        question_with_error = f"{user_question}, SQL오류: {sql_error}"
        system_prompt = PROMPT_NL2SQL.format(
            user_question=question_with_error,
            today=prompt_today
        )

    qna_id = qna_manager.create_qna_id(trace_id)

    prompt = ChatPromptTemplate.from_messages(
        [SystemMessage(content=system_prompt), ("human", user_question)]
    )

    logger.info("===== safeguard(Q) =====")
    qna_manager.update_question(
        qna_id=qna_id,
        question=prompt,
        model="qwen_14b"
    )

    guard_chain = prompt | llm
    output = guard_chain.invoke({"user_question": user_question})

    safe_query = handle_sql_code_block(output)

    logger.info("===== safeguard(A) =====")

    # 쿼리 변경 여부 로깅
    if safe_query != unsafe_query:
        logger.info("Query was modified by safeguard")
        logger.info(f"Original query: {unsafe_query}")
        logger.info(f"Modified query: {safe_query}")
    else:
        logger.info("Query was not modified by safeguard")

    qna_manager.record_answer(qna_id, safe_query)

    return safe_query
