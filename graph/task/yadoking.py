from typing import List

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from database.database_service import DatabaseService
from graph.models import qwen_llm
from llm_admin.qna_manager import QnAManager

database_service = DatabaseService()
qna_manager = QnAManager()

async def yadoking(trace_id: str, user_question: str, last_data: List[str]) -> str:
    """이전 대화 맥락을 바탕으로 현재 질문 재해석
    Args:
        last_data: 이전 3개의 질의응답 기록
    Returns:
        재해석된 질문 문자열
    """
    last_data_str = ''
    for x in last_data:
        last_template = "\n제공된 맥락"+\
                f"\n- 이전 질문에 대한 답변\n{x['last_answer']}\n"
        last_data_str += last_template

    system_prompt = database_service.get_prompt(
        node_nm='create_query', prompt_nm='historian'
    )[0]['prompt'].format(last_data_str=last_data_str)

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            ("human", user_question)
        ]
    )

    print("=" * 40 + "Yadoran(Q)" + "=" * 40)
    qna_id = qna_manager.create_question(
        trace_id=trace_id,
        question=prompt,
        model="qwen_14b"
    )

    checkpoint_chain = prompt | qwen_llm
    history_check = checkpoint_chain.invoke({"user_question": user_question})

    print("=" * 40 + "Yadoran(A)" + "=" * 40)
    print(history_check)
    qna_manager.record_answer(qna_id, history_check)

    return history_check