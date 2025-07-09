from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from graph.models import qwen_llm
from graph.prompts.prompts_guardian import PROMPT_NODATA
from llm_admin.qna_manager import QnAManager
from utils.common.chat_history import convert_to_chat_history
from utils.logger import setup_logger

qna_manager = QnAManager()
logger = setup_logger("nodata")


async def no_data(trace_id: str, user_question: str, nodata_history: dict) -> str:
    """조회해봤지만 데이터가 없습니다
    Args:
        trace_id: 추적 ID
        user_question: 사용자 질문
        nodata_history: chain_id별로 그룹화된 과거 대화 이력
    Returns:
        없다는 답변
    """
    logger.info(
        f"Generating 'no data' response for question: '{user_question[:50]}...'"
    )

    qna_id = qna_manager.create_qna_id(trace_id)

    chat_history_prompt = convert_to_chat_history(
        nodata_history,
        required_fields=["user_question", "final_answer"],
        human_field="user_question",
        ai_field="final_answer",
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=PROMPT_NODATA),
            *chat_history_prompt,
            ("human", user_question),
        ]
    )

    logger.info("===== Nodata(Q) =====")
    qna_manager.update_question(
        qna_id=qna_id,
        question=prompt,
        model="qwen_14b"
    )

    nodata_chain = prompt | qwen_llm
    final_answer = nodata_chain.invoke({"user_question": user_question})

    logger.info("===== Nodata(A) =====")
    logger.info(f"Generated 'no data' response (length: {len(final_answer)})")
    logger.info(f"Response content: {final_answer}")
    qna_manager.record_answer(qna_id, final_answer)

    return final_answer
