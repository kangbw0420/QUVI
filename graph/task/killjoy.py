from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from graph.models import qwen_high
from graph.prompts.prompts_guardian import PROMPT_KILLJOY
from llm_admin.qna_manager import QnAManager
from utils.logger import setup_logger
from utils.common.chat_history import convert_to_chat_history

qna_manager = QnAManager()
logger = setup_logger("killjoy")


async def kill_joy(
    trace_id: str, 
    user_question: str, 
    killjoy_history: dict
) -> str:
    """저랑 놀려고 하지 마세요
    Args:
        trace_id: 추적 ID
        user_question: 사용자 질문
        killjoy_history: chain_id별로 그룹화된 과거 대화 이력
    Returns:
        일상 대화 대신 재무 데이터 조회 대화를 유도하는 답변
    """
    logger.info(f"Processing non-financial question: {user_question}")

    chat_history_prompt = convert_to_chat_history(
        killjoy_history,
        required_fields=["user_question", "final_answer"],
        human_field="user_question",
        ai_field="final_answer"
    )

    qna_id = qna_manager.create_qna_id(trace_id)

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=PROMPT_KILLJOY),
            *chat_history_prompt,
            ("human", user_question),
        ]
    )

    logger.info("===== killjoy(Q) =====")
    qna_manager.update_question(
        qna_id=qna_id,
        question=prompt,
        model="qwen_14b"
    )

    kill_chain = prompt | qwen_high
    final_answer = kill_chain.invoke({"user_question": user_question})

    logger.info("===== killjoy(A) =====")
    logger.info(f"Generated response: {final_answer[:100]}...")
    qna_manager.record_answer(qna_id, final_answer)

    return final_answer
