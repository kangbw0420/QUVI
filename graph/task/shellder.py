from typing import List

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from database.database_service import DatabaseService
from graph.models import qwen_llm
from llm_admin.qna_manager import QnAManager

database_service = DatabaseService()
qna_manager = QnAManager()

async def shellder(trace_id: str, user_question: str, last_data: List[str]) -> str:
    """이전 대화 맥락을 기반으로 현재 질문이 금융 데이터 조회와 관련있는지 검사
    Args:
        last_data: 이전 3개의 질의응답 기록 
    Returns:
        "no"(관련없음), "1"(맥락 연결), "0"(새로운 질의) 중 하나
    """
    last_data_str = ''
    for x in last_data:
        last_template = "\n제공된 맥락"+\
                f"\n- 이전 질문\n{x['last_question']}\n"+\
                f"\n- 이전 질문에 대한 답변\n{x['last_answer']}\n"
        last_data_str += last_template

    system_prompt = database_service.get_prompt(
        node_nm='create_query', prompt_nm='checkpoint'
    )[0]['prompt'].format(last_data_str=last_data_str)

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            ("human", user_question)
        ]
    )

    print("=" * 40 + "Yadon(Q)" + "=" * 40)
    qna_id = qna_manager.create_question(
        trace_id=trace_id,
        question=prompt,
        model="qwen_14b"
    )

    checkpoint_chain = prompt | qwen_llm
    shellder = checkpoint_chain.invoke({"user_question": user_question})

    print("=" * 40 + "Yadon(A)" + "=" * 40)
    print(shellder)
    qna_manager.record_answer(qna_id, shellder)

    return shellder