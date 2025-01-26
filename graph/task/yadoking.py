from typing import List
from dotenv import load_dotenv

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from database.database_service import DatabaseService
from graph.models import selector, qwen_llm
from llm_admin.qna_manager import QnAManager

load_dotenv()
database_service = DatabaseService()
qna_manager = QnAManager()

async def yadoking(trace_id: str, user_question: str, last_data: List[str]) -> str:
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