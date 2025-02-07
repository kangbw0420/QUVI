from typing import List

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from database.database_service import DatabaseService
from graph.models import qwen_llm
from llm_admin.qna_manager import QnAManager

database_service = DatabaseService()
qna_manager = QnAManager()

async def no_data(trace_id: str, user_question: str) -> str:
    """조회해봤지만 데이터가 없습니다
    Returns:
        없다는 답변
    """
    system_prompt = database_service.get_prompt(
        node_nm='nodata', prompt_nm='system'
    )[0]['prompt']

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            ("human", user_question)
        ]
    )

    print("=" * 40 + "Nodata(Q)" + "=" * 40)
    qna_id = qna_manager.create_question(
        trace_id=trace_id,
        question=prompt,
        model="qwen_14b"
    )

    referral_chain = prompt | qwen_llm
    final_answer = referral_chain.invoke({"user_question": user_question})

    print("=" * 40 + "Nodata(A)" + "=" * 40)
    print(final_answer)
    qna_manager.record_answer(qna_id, final_answer)

    return final_answer