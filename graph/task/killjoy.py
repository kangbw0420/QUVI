from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from core.postgresql import get_prompt
from graph.models import qwen_high
from llm_admin.qna_manager import QnAManager
from utils.logger import setup_logger

qna_manager = QnAManager()
logger = setup_logger('killjoy')

async def kill_joy(trace_id: str, user_question: str) -> str:
    """저랑 놀려고 하지 마세요
    Returns:
        일상 대화 대신 재무 데이터 조회 대화를 유도하는 답변
    """
    logger.info(f"Processing non-financial question: {user_question}")

    system_prompt = get_prompt(
        node_nm='killjoy', prompt_nm='system'
    )[0]['prompt']

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            ("human", user_question)
        ]
    )

    logger.debug("===== killjoy(Q) =====")
    qna_id = qna_manager.create_question(
        trace_id=trace_id,
        question=prompt,
        model="qwen_14b"
    )

    kill_chain = prompt | qwen_high
    final_answer = kill_chain.invoke({"user_question": user_question})

    logger.debug("===== killjoy(A) =====")
    logger.info(f"Generated response: {final_answer[:100]}...")
    qna_manager.record_answer(qna_id, final_answer)

    return final_answer