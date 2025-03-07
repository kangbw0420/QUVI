import re
from datetime import datetime

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from database.database_service import DatabaseService
from graph.models import qwen_llm
from llm_admin.qna_manager import QnAManager

database_service = DatabaseService()
qna_manager = QnAManager()

async def guard_query(
    trace_id: str,
    unsafe_query: str,
    user_question: str,
    selected_table: str,
    flags: dict,
    sql_error: str = ""
    ) -> str:
    """에러가 발생했거나 날짜가 틀릴 수 있는 쿼리를 체크
    Returns:
        수정된 쿼리(문제 없으면 쿼리 그대로 return)
    """
    today = datetime.now()
    prompt_today = today.strftime("%Y년 %m월 %d일")
    
    if flags["query_error"]:
        system_prompt = database_service.get_prompt(
            node_nm='safeguard', prompt_nm='error'
        )[0]['prompt'].format(user_question=user_question, today=prompt_today, unsafe_query=unsafe_query, sql_error=sql_error)
    else:
        system_prompt = database_service.get_prompt(
            node_nm='safeguard', prompt_nm=selected_table
        )[0]['prompt'].format(user_question=user_question, today=prompt_today, unsafe_query=unsafe_query)

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            ("human", user_question)
        ]
    )

    print("=" * 40 + "safeguard(Q)" + "=" * 40)
    qna_id = qna_manager.create_question(
        trace_id=trace_id,
        question=prompt,
        model="qwen_14b"
    )

    guard_chain = prompt | qwen_llm
    output = guard_chain.invoke({"user_question": user_question})
    
    match = re.search(r"```sql\s*(.*?)\s*```", output, re.DOTALL)
    if match:
        safe_query = match.group(1)
    else:
        match = re.search(r"SELECT.*", output, re.DOTALL)
        if match:
            safe_query = match.group(0)

        else:
            raise ValueError("SQL 쿼리를 찾을 수 없습니다.")

    print("=" * 40 + "safeguard(A)" + "=" * 40)
    print(safe_query)
    qna_manager.record_answer(qna_id, safe_query)

    return safe_query