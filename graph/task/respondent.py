from typing import Optional, Tuple
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from database.database_service import DatabaseService
from graph.models import solver, qwen_llm
from utils.retriever import retriever
from llm_admin.qna_manager import QnAManager

database_service = DatabaseService()
qna_manager = QnAManager()

async def response(trace_id: str, user_question, selected_table: str, column_list = None, date_info: Optional[Tuple[str, str]] = None) -> str:
    """쿼리 실행 결과를 바탕으로 자연어 응답을 생성합니다.
    Returns:
        str: 생성된 자연어 응답.
    Raises:
        ValueError: 프롬프트 템플릿 로딩 실패 또는 LLM 응답 생성 실패시.
    """
    output_parser = StrOutputParser()

    if selected_table == 'api':
        system_prompt = database_service.get_prompt(node_nm='respondent', prompt_nm='api')[0]['prompt']
    else:
        system_prompt = database_service.get_prompt(node_nm='respondent', prompt_nm='sql')[0]['prompt']

    if selected_table == 'api':
        collection_name = "shots_respondent_api"
    else:
        collection_name = "shots_respondent_sql"

    few_shots = await retriever.get_few_shots(
        query_text=user_question,
        collection_name=collection_name,
        top_k=3
    )
    few_shot_prompt = []
    for example in reversed(few_shots):
        if "stats" in example:
            # 날짜 정보가 있는 경우와 없는 경우를 구분
            if "date" in example:
                human_with_stats_date = (
                    f'사용 가능한 column_nm:\n{example["stats"]}\n\n'
                    f'사용자의 질문:\n{example["date"]}. {example["input"]}'
                )
                few_shot_prompt.append(("human", human_with_stats_date))
            else:
                human_with_stats = f'사용 가능한 column_nm:\n{example["stats"]}\n\n사용자의 질문:\n{example["input"]}'
                few_shot_prompt.append(("human", human_with_stats))
        else:
            few_shot_prompt.append(("human", example["input"]))
        few_shot_prompt.append(("ai", example["output"]))

    # column_list를 문자열로 변환
    column_list_str = ", ".join(column_list) if column_list else ""
    
    if date_info:
        (from_date, to_date) = date_info
        formatted_user_question = f"시작 시점: {from_date}, 종료 시점: {to_date}.  {user_question}"
    else:
        formatted_user_question = user_question

    human_prompt = database_service.get_prompt(node_nm='respondent', prompt_nm='human')[0]['prompt'].format(
        column_list=column_list_str, user_question=formatted_user_question
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            *few_shot_prompt,
            ("human", human_prompt),
        ]
    )

    print("=" * 40 + "respondent(Q)" + "=" * 40)
    qna_id = qna_manager.create_question(
        trace_id=trace_id,
        question=prompt,
        model="qwen_14b"
    )

    chain = prompt | solver | output_parser
    raw_answer = chain.invoke({"human_prompt": user_question})

    # Remove code block markers if present
    fstring_answer = raw_answer.strip()
    if fstring_answer.startswith('```python\n'):
        fstring_answer = fstring_answer[10:]
    elif fstring_answer.startswith('```python'):
        fstring_answer = fstring_answer[9:]
    
    if fstring_answer.endswith('\n```'):
        fstring_answer = fstring_answer[:-4]
    elif fstring_answer.endswith('```'):
        fstring_answer = fstring_answer[:-3]

    print("=" * 40 + "respondent(A)" + "=" * 40)
    print(fstring_answer)
    qna_manager.record_answer(qna_id, fstring_answer)

    return fstring_answer
