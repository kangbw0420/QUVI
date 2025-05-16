from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from graph.models import qwen_llm
from graph.prompts.prompts_guardian import PROMPT_NODATA
from llm_admin.qna_manager import QnAManager
from utils.logger import setup_logger

qna_manager = QnAManager()
logger = setup_logger("nodata")


async def no_data(
    trace_id: str, user_question: str, chat_history_prompt: list[tuple[str, str]]
) -> str:
    """조회해봤지만 데이터가 없습니다
    Returns:
        없다는 답변
    """
    logger.info(
        f"Generating 'no data' response for question: '{user_question[:50]}...'"
    )
    
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=PROMPT_NODATA),
            *chat_history_prompt,
            ("human", user_question),
        ]
    )

    logger.debug("===== Nodata(Q) =====")
    qna_id = qna_manager.create_question(
        trace_id=trace_id, question=prompt, model="qwen_14b"
    )

    nodata_chain = prompt | qwen_llm
    final_answer = nodata_chain.invoke({"user_question": user_question})

    logger.debug("===== Nodata(A) =====")
    logger.info(f"Generated 'no data' response (length: {len(final_answer)})")
    logger.debug(f"Response content: {final_answer}")
    qna_manager.record_answer(qna_id, final_answer)

    return final_answer
