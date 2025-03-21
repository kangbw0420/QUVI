from typing import List

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from database.database_service import DatabaseService
from graph.models import qwen_llm
from llm_admin.qna_manager import QnAManager
from utils.logger import setup_logger

database_service = DatabaseService()
qna_manager = QnAManager()
logger = setup_logger('yadoran')


async def yadoking(trace_id: str, user_question: str, last_data: List[str], today: str) -> str:
    """이전 대화 맥락을 바탕으로 현재 질문 재해석
    Args:
        last_data: 이전 3개의 질의응답 기록
    Returns:
        재해석된 질문 문자열
    """
    last_data_chat = []
    for x in last_data:
        last_data_chat.append(("human", x['last_question']))
        last_data_chat.append(("ai", x['last_answer']))

    system_prompt = database_service.get_prompt(
        node_nm='yadoran', prompt_nm='system'
    )[0]['prompt'].format(today=today)

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            *last_data_chat,
            ("human", user_question)
        ]
    )

    logger.debug("===== Yadoran(Q) =====")
    qna_id = qna_manager.create_question(
        trace_id=trace_id,
        question=prompt,
        model="qwen_14b"
    )

    checkpoint_chain = prompt | qwen_llm
    history_check = checkpoint_chain.invoke({"user_question": user_question})

    logger.debug("===== Yadoran(A) =====")
    logger.info(f"Reinterpreted question (length: {len(history_check)})")
    logger.debug(f"Reinterpreted question: {history_check}")
    qna_manager.record_answer(qna_id, history_check)

    return history_check