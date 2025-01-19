import json
import re
from typing import Union, Sequence, Dict, Any
from dotenv import load_dotenv
from datetime import datetime

from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Result
from sqlalchemy.sql.expression import Executable

from database.database_service import DatabaseService
from llm_models.models import llama_70b_llm, qwen_llm, qwen_llm_7b, llama_8b_llm
from utils.config import Config
from utils.retriever import retriever
from llm_admin.qna_manager import QnAManager

load_dotenv()
database_service = DatabaseService()
qna_manager = QnAManager()

WEEKDAYS = {
    0: '월',
    1: '화',
    2: '수',
    3: '목',
    4: '금',
    5: '토',
    6: '일'
}

async def select_table(trace_id: str, user_question: str, last_data: str = "") -> str:
    """사용자의 질문으로부터 테이블을 선택
    Returns:
        str: 'aicfo_get_cabo_XXXX'의 테이블
    Raises:
        ValueError: 질문이 분석 가능한 형식이 아닌 경우.
    """
    output_parser = StrOutputParser()

    system_prompt = database_service.get_prompt(node_nm='select_table', prompt_nm='system')[0]['prompt']
    contents = system_prompt + last_data if len(last_data)>1 else system_prompt

    few_shots = await retriever.get_few_shots(
        query_text=user_question, collection_name="shots_selector", top_k=5
    )
    few_shot_prompt = []
    for example in few_shots:
        few_shot_prompt.append(("human", example["input"]))
        few_shot_prompt.append(("ai", example["output"]))

    SELECT_TABLE_PROMPT = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=contents),
            *few_shot_prompt,
            ("human", user_question)
        ]
    )

    print("=" * 40 + "selector(Q)" + "=" * 40)
    qna_id = qna_manager.create_question(
        trace_id=trace_id,
        question=SELECT_TABLE_PROMPT,
        model="qwen_7b"
    )

    select_table_chain = SELECT_TABLE_PROMPT | qwen_llm_7b | output_parser
    selected_table = select_table_chain.invoke({"user_question": user_question})

    print("=" * 40 + "selector(A)" + "=" * 40)
    print(selected_table)
    qna_manager.record_answer(qna_id, selected_table)

    return selected_table

'''
async def analyze_user_question(trace_id: str, user_question: str, selected_table: str, today: str, last_data: str = "") -> str:
    """사용자의 질문을 분석하여 표준화된 형식으로 변환
    Returns:
        str: 'aicfo_get_cabo_XXXX[질문내용]' 형식으로 변환된 질문
    Raises:
        ValueError: 질문이 분석 가능한 형식이 아닌 경우.
    """
    output_parser = StrOutputParser()

    system_prompt = database_service.get_prompt(node_nm='analyze_user_question', prompt_nm='system')[0]['prompt'].format(today=today)

    schema_prompt = (
        f"테이블: aicfo_get_all_{selected_table}\n"
        + "칼럼명:\n"
        + json.loads(database_service.get_prompt(node_nm='analyze_user_question', prompt_nm='selected_table')[0]['prompt'])[selected_table]
    )

    contents = system_prompt + schema_prompt + last_data if len(last_data) > 1 else system_prompt + schema_prompt

#    few_shots = await retriever.get_few_shots(
#        query_text= user_question, collection_name="shots_analyzer", top_k=6
#    )
#    few_shot_prompt = []
#    for example in few_shots:
#        few_shot_prompt.append(("human", example["input"]))
#        few_shot_prompt.append(("ai", example["output"]))

    ANALYZE_PROMPT = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=contents),
#            *few_shot_prompt,
            ("human", user_question)
        ]
    )

    print("=" * 40 + "analyzer(Q)" + "=" * 40)
    qna_id = qna_manager.create_question(
        trace_id=trace_id,
        question=ANALYZE_PROMPT,
        model="llama_70b"
    )

#    analyze_chain = ANALYZE_PROMPT | llama_70b_llm | output_parser
#    analyzed_question = analyze_chain.invoke({"user_question": user_question})

    analyzed_question = "잠만보 귀여워"
    print("=" * 40 + "analyzer(A)" + "=" * 40)
    print(analyzed_question)
    qna_manager.record_answer(qna_id, analyzed_question)

    return analyzed_question
'''

async def create_query(trace_id: str, selected_table, user_question: str, today: str) -> str:
    """분석된 질문으로부터 SQL 쿼리를 생성
    Returns:
        str: 생성된 SQL 쿼리문
    Raises:
        ValueError: SQL 쿼리를 생성할 수 없거나, 추출 패턴이 매치되지 않는 경우
        TypeError: LLM 응답이 예상된 형식이 아닌 경우.
    """
    try:
        try:
            system_prompt = database_service.get_prompt(node_nm='create_query', prompt_nm=selected_table)[0]['prompt'].format(today=today)
            
        except FileNotFoundError as e:
            system_prompt = database_service.get_prompt(node_nm='create_query', prompt_nm='system')[0]['prompt'].format(today=today)

        schema_prompt = (
            f"테이블: aicfo_get_all_{selected_table}\n"
            + "칼럼명:\n"
            # analyzer에서 사용했던 스키마 테이블 재사용 - node_nm/prompt_nm 변경??
            + json.loads(database_service.get_prompt(node_nm='analyze_user_question', prompt_nm='selected_table')[0]['prompt'])[selected_table]
        )

        # 콜렉션 이름은 shots_trsc, shots_amt와 같이 구성됨
        collection_name = f"shots_{selected_table}"

        few_shots = await retriever.get_few_shots(
            query_text=user_question,
            collection_name=collection_name,
            top_k=3
        )
        few_shot_prompt = []
        for example in few_shots:
            if "date" in example:
                human_with_date = f'{example["input"]}, 오늘: {example["date"]}.'
            else:
                human_with_date = example["input"]
            few_shot_prompt.append(("human", human_with_date))
            few_shot_prompt.append(("ai", example["output"]))

        today_date = datetime.strptime(today, "%Y-%m-%d")
        formatted_today = today_date.strftime("%Y%m%d")
        weekday = WEEKDAYS[today_date.weekday()]

        formatted_question = f"{user_question}, 오늘: {formatted_today} {weekday}요일."

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_prompt + schema_prompt),
                *few_shot_prompt,
                ("human", formatted_question),
            ]
        )

        print("=" * 40 + "nl2sql(Q)" + "=" * 40)
        qna_id = qna_manager.create_question(
            trace_id=trace_id,
            question=prompt,
            model="qwen"
        )

        chain = prompt | qwen_llm
        output = chain.invoke(
            {"user_question": formatted_question}
        )  # LLM 응답 (AIMessage 객체)

        # 출력에서 SQL 쿼리 추출
        match = re.search(r"```sql\s*(.*?)\s*```", output, re.DOTALL)
        if match:
            sql_query = match.group(1)
        else:
            match = re.search(r"SELECT.*?;", output, re.DOTALL)
            if match:
                sql_query = match.group(0)

            else:
                raise ValueError("SQL 쿼리를 찾을 수 없습니다.")
        
        print("=" * 40 + "nl2sql(A)" + "=" * 40)
        print(output)
        qna_manager.record_answer(qna_id, output)

        return sql_query.strip()

    except Exception as e:
        raise


def execute_query(command: Union[str, Executable], fetch="all") -> Union[Sequence[Dict[str, Any]], Result]:  # type: ignore
    """SQL 쿼리를 실행하고 결과를 반환합니다.
    Returns:
        Union[Sequence[Dict[str, Any]], Result]: 쿼리 실행 결과.
        fetch='all': 모든 결과 행을 딕셔너리 리스트로 반환.
        fetch='one': 첫 번째 결과 행을 딕셔너리로 반환.
        fetch='cursor': 커서 객체 직접 반환.
    Raises:
        ValueError: fetch 파라미터가 유효하지 않은 경우.
        TypeError: command가 문자열이나 Executable이 아닌 경우.
        Exception: 데이터베이스 연결 또는 쿼리 실행 중 오류 발생시.
    """
    try:
        parameters = {}
        execution_options = {}

        # URL encode the password to handle special characters
        from urllib.parse import quote_plus

        password = quote_plus(str(Config.DB_PASSWORD))
        db_url = f"postgresql://{Config.DB_USER}:{password}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_DATABASE}"

        engine = create_engine(db_url)

        with engine.begin() as connection:
            # SQLAlchemy를 활용해 실행 가능한 쿼리 객체로 변경
            if isinstance(command, str):
                command = text(command)
            elif isinstance(command, Executable):
                pass
            else:
                raise TypeError(f"Query expression has unknown type: {type(command)}")
            
            # # (production) 사용하려는 스키마 지정
            # schemaQuery = f"SET search_path TO {Config.DB_SCHEMA}"
            # print(f"::::::::::::::: schemaQuery : {schemaQuery}")
            # connection.execute(text(schemaQuery))

            cursor = connection.execute(
                command,
                parameters,
                execution_options=execution_options,
            )

            if cursor.returns_rows:
                if fetch == "all":
                    rows = cursor.fetchall()
                    result = [x._asdict() for x in rows]
                elif fetch == "one":
                    first_result = cursor.fetchone()
                    if first_result is None:
                        print("No results found")
                        result = []
                    else:
                        print("Converting single row to dictionary")
                        result = [first_result._asdict()]
                elif fetch == "cursor":
                    print("Returning cursor directly")
                    return cursor
                else:
                    print(f"Invalid fetch mode: {fetch}")
                    raise ValueError(
                        "Fetch parameter must be either 'one', 'all', or 'cursor'"
                    )

                print(f"Returning {len(result)} results")
                return result
            else:
                print("Query does not return any rows")
                return []

    except Exception as e:
        print(f"Error type: {type(e)}")
        print(f"Error message: {str(e)}")
        import traceback

        print("Full traceback:")
        traceback.print_exc()
        raise


async def sql_response(trace_id: str, user_question, query_result_stats = None, query_result = None) -> str:
    """쿼리 실행 결과를 바탕으로 자연어 응답을 생성합니다.
    Returns:
        str: 생성된 자연어 응답.
    Raises:
        ValueError: 프롬프트 템플릿 로딩 실패 또는 LLM 응답 생성 실패시.
    """
    output_parser = StrOutputParser()

    system_prompt = database_service.get_prompt(node_nm='sql_response', prompt_nm='system')[0]['prompt']
    
    # 통곗값이 있으면 통곗값을 쓰고, 아니면 결과 자체를 사용
    human_prompt = database_service.get_prompt(node_nm='sql_response', prompt_nm='human')[0]['prompt'].format(
        query_result_stats=query_result_stats if query_result_stats is not None else query_result, user_question=user_question
    )

    # 앞의 사례와 다르게 query_text가 human_prompt임에 유의
    few_shots = await retriever.get_few_shots(
        query_text=human_prompt, collection_name="shots_respondent", top_k=3
    )
    few_shot_prompt = []
    for example in few_shots:
        few_shot_prompt.append(("human", example["input"]))
        few_shot_prompt.append(("ai", example["output"]))

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            *few_shot_prompt,
            ("human", human_prompt)
        ]
    )

    print("=" * 40 + "respondent(Q)" + "=" * 40)
    qna_id = qna_manager.create_question(
        trace_id=trace_id,
        question=prompt,
        model="llama_70b"
    )

    chain = prompt | llama_70b_llm | output_parser
    output = chain.invoke({"human_prompt": user_question})

    print("=" * 40 + "respondent(A)" + "=" * 40)
    print(output)
    qna_manager.record_answer(qna_id, output)

    return output