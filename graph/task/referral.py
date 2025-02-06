from typing import List

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from database.database_service import DatabaseService
from graph.models import qwen_llm
from llm_admin.qna_manager import QnAManager

database_service = DatabaseService()
qna_manager = QnAManager()

async def question_referral(trace_id: str, user_question: str) -> str:
    """이것도 질문해보시겠습니까?
    Returns:
        추천 질문 리스트
    """
    system_prompt = database_service.get_prompt(
        node_nm='create_query', prompt_nm='referral'
    )[0]['prompt']

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            ("human", user_question)
        ]
    )

    print("=" * 40 + "Referral(Q)" + "=" * 40)
    qna_id = qna_manager.create_question(
        trace_id=trace_id,
        question=prompt,
        model="qwen_14b"
    )

    referral_chain = prompt | qwen_llm
    referral_list = referral_chain.invoke({"user_question": user_question})

    print("=" * 40 + "Referral(A)" + "=" * 40)
    print(referral_list)
    qna_manager.record_answer(qna_id, referral_list)

    return referral_list