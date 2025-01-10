import re
from typing import Union, Sequence, Dict, Any
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from sqlalchemy import create_engine, text
from sqlalchemy.sql.expression import Executable
from sqlalchemy.engine import Result

from .utils import load_prompt
from llm_models.models import llama_70b_llm, llama_8b_llm, qwen_llm
from utils.config import Config
from utils.retriever import retriever

load_dotenv()

async def select_table(user_question: str, last_data: str = "") -> str:
    """사용자의 질문으로부터 테이블을 선택
    Returns:
        str: 'aicfo_get_cabo_XXXX'의 테이블
    Raises:
        ValueError: 질문이 분석 가능한 형식이 아닌 경우.
    """
    output_parser = StrOutputParser()

    """
    프롬프트는 세 부분으로 구성됩니다.
    1) 시스템 프롬프트
    2) 퓨 샷
    3) 사용자 프롬프트 (사용자의 질문만)        
    """
    system_prompt = load_prompt("prompts/select_table/system.prompt")
    # 추가) system_prompt = postgresql에서 get_prompt(node=select_table, prompt_name=system)

    contents = system_prompt + last_data if len(last_data)>1 else system_prompt

    few_shots = await retriever.get_few_shots(
        query_text=user_question, task_type="selector", collection_name="shots_selector"
    )

    few_shot_prompt = []
    for example in few_shots:
        few_shot_prompt.append(("human", example["input"]))
        few_shot_prompt.append(("ai", example["output"]))

    SELECT_TABLE_PROMPT = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=contents),
            *few_shot_prompt,
            ("human", "{user_question}\nAI:"),
        ]
    )

    select_table_chain = SELECT_TABLE_PROMPT | llama_70b_llm | output_parser
    selected_table = select_table_chain.invoke({"user_question": user_question})

    return selected_table


async def analyze_user_question(user_question: str, selected_table: str, today: str, last_data: str = "") -> str:
    """사용자의 질문을 분석하여 표준화된 형식으로 변환
    Returns:
        str: 'aicfo_get_cabo_XXXX[질문내용]' 형식으로 변환된 질문
    Raises:
        ValueError: 질문이 분석 가능한 형식이 아닌 경우.
    """
    output_parser = StrOutputParser()

    """
    프롬프트는 세 부분으로 구성됩니다.
    1) 시스템 프롬프트
    2) 퓨 샷
    3) 사용자 프롬프트 (사용자의 질문만)        
    """
    print("\n=== Analyze User Question Started ===")
    print(f"Processing question: {user_question}")
    system_prompt = load_prompt("prompts/analyze_user_question/system.prompt").format(today=today)
    # 추가) system_prompt = postgresql에서 get_prompt(node=analyze_user_question, prompt_name=system).format(today=today)

    schema_prompt = (
        f"테이블: aicfo_get_all_{selected_table}\n"
        + "칼럼명:\n"
        + load_prompt("prompts/schema.json")[selected_table]
        # 추가) + postgresql에서 get_prompt(node=analyze_user_question, prompt_name=selected_table)
    )

    contents = system_prompt + schema_prompt + last_data if len(last_data) > 1 else system_prompt + schema_prompt
    
    few_shots = await retriever.get_few_shots(
        query_text= user_question, task_type="analyzer", collection_name="shots_analyzer"
    )

    few_shot_prompt = []
    for example in few_shots:
        few_shot_prompt.append(("human", example["input"]))
        few_shot_prompt.append(("ai", example["output"]))

    ANALYZE_PROMPT = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=contents),
            *few_shot_prompt,
            ("human", "{user_question}\nAI:"),
        ]
    )

    analyze_chain = ANALYZE_PROMPT | llama_70b_llm | output_parser
    analyzed_question = analyze_chain.invoke({"user_question": user_question})

    print(f"Final analyzed question: {analyzed_question}")
    return analyzed_question


async def create_query(selected_table, analyzed_question: str, today: str) -> str:
    """분석된 질문으로부터 SQL 쿼리를 생성
    Returns:
        str: 생성된 SQL 쿼리문
    Raises:
        ValueError: SQL 쿼리를 생성할 수 없거나, 추출 패턴이 매치되지 않는 경우
        TypeError: LLM 응답이 예상된 형식이 아닌 경우.
    """
    try:

        """
        프롬프트는 네 부분으로 구성됩니다.
        1) 시스템 프롬프트
        2) 스키마 프롬프트 (테이블의 칼럼명을 가져옵니다.)
        3) 퓨 샷
        4) 사용자 프롬프트 (오늘 날짜 및 분석된 질의)
        """
        try:
            prompt_file = f"prompts/create_query/{selected_table}.prompt"
            system_prompt = load_prompt(prompt_file).format(today=today)
            
        except FileNotFoundError as e:
            system_prompt = load_prompt("prompts/create_query/system.prompt").format(
                today=today
            )

        schema_prompt = (
            f"테이블: aicfo_get_all_{selected_table}\n"
            + "칼럼명:\n"
            + load_prompt("prompts/schema.json")[selected_table]
        )

        # 콜렉션 이름은 shots_trsc, shots_amt와 같이 구성됨
        collection_name = f"shots_{selected_table}"

        # # retriever를 사용하여 동적으로 few-shot 예제 가져오기
        few_shots = await retriever.get_few_shots(
            query_text=analyzed_question,
            task_type="creator",
            collection_name=collection_name,
        )

        few_shot_prompt = []
        for example in few_shots:
            few_shot_prompt.append(("human", example["input"]))
            few_shot_prompt.append(("ai", example["output"]))

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_prompt + schema_prompt),
                *few_shot_prompt,
                ("human", analyzed_question),
            ]
        )
        chain = prompt | qwen_llm

        # LLM 호출 및 출력 받기
        output = chain.invoke(
            {"analyzed_question": analyzed_question}
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
    print("\n=== Execute Query Started ===")
    print(f"Query to execute: {command}")
    print(f"Fetch mode: {fetch}")

    try:
        parameters = {}
        execution_options = {}

        # URL encode the password to handle special characters
        from urllib.parse import quote_plus

        password = quote_plus(str(Config.DB_PASSWORD))
        db_url = f"postgresql://{Config.DB_USER}:{password}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_DATABASE}"

        engine = create_engine(db_url)

        print("\n=== Executing Query ===")
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
                print("\n=== Processing Results ===")
                if fetch == "all":
                    rows = cursor.fetchall()
                    print(f"Retrieved {len(rows)} rows")
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
        print("\n=== Error in execute_query ===")
        print(f"Error type: {type(e)}")
        print(f"Error message: {str(e)}")
        import traceback

        print("Full traceback:")
        traceback.print_exc()
        raise


def sql_response(user_question, query_result_stats = None, query_result = None) -> str:
    """쿼리 실행 결과를 바탕으로 자연어 응답을 생성합니다.
    Returns:
        str: 생성된 자연어 응답.
    Raises:
        ValueError: 프롬프트 템플릿 로딩 실패 또는 LLM 응답 생성 실패시.
    """
    output_parser = StrOutputParser()

    system_prompt = load_prompt("prompts/sql_response/system.prompt")
    few_shots = load_prompt("prompts/sql_response/fewshots.json")
    few_shot_prompt = []
    for example in few_shots:
        few_shot_prompt.append(("human", example["input"]))
        few_shot_prompt.append(("ai", example["output"]))

    # query_result_stats vs query_result
    human_prompt = load_prompt("prompts/sql_response/human.prompt").format(
        query_result_stats=query_result_stats if query_result_stats is not None else query_result, user_question=user_question
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            *few_shot_prompt,
            HumanMessage(content=human_prompt),
        ]
    )
    chain = prompt | llama_70b_llm | output_parser

    output = chain.invoke({"user_question": user_question})
    return output


def columns_filter(query_result: list, selected_table_name:str):
    result = query_result

    import json
    with open("temp.json", 'r', encoding='utf-8') as f: # 테이블에 따른 컬럼리스트 (type: JSON)
        columns_list = json.load(f)
        
    # node에서 query_result 의 element 존재유무를 검사했으니 
    # row가 갖고 있는 column name 기준으로 '거래내역'과 '잔액'을 구분
    # amt 잔액, trsc 거래내역
    if selected_table_name == "trsc":   # '거래내역'
        filtered_result = []    # 필터링한 결과를 출력할 변수
        # view_dv로 인텐트트 구분
        # 모든 row가 갖고 있는 column name list는 같으므로
        if 'view_dv' in result[0]:
            intent = columns_list['trsc'][result[0]['view_dv']]
            for x in result:
                x = {k: v for k, v in x.items() if k in intent}
                filtered_result.append(x)
        else:   # view_dv가 없기 때문에 '전체'에 해당되는 column list만 출력
            intent = columns_list['trsc']['전체']
            for x in result:
                x = {k: v for k, v in x.items() if k in intent}
                filtered_result.append(x)
        return filtered_result
    elif selected_table_name == "amt": # '잔액'
        filtered_result = []    # 필터링한 결과를 출력할 변수
        # view_dv로 세부 항목 구분
        # 모든 row가 갖고 있는 column name list는 같으므로
        if 'view_dv' in result[0]:
            intent = columns_list['amt'][result[0]['view_dv']]
            for x in result:
                x = {k: v for k, v in x.items() if k in intent}
                filtered_result.append(x)
        else:   # view_dv가 없기 때문에 '전체'에 해당되는 column list만 출력
            intent = columns_list['amt']['전체']
            for x in result:
                x = {k: v for k, v in x.items() if k in intent}
                filtered_result.append(x)
        return filtered_result
    else:                       # 해당사항 없으므로 본래 resul값 출력 
        return result
