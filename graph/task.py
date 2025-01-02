import re, os
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

from prompts.retriever import retriever
import asyncio

load_dotenv()


def analyze_user_question(user_question: str) -> str:
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
    system_prompt = load_prompt("prompts/analyze_user_question/system.prompt")

    # few_shots = await retriever.get_few_shots(
    #     query_text=user_question,
    #     task_type="analyzer",
    #     collection_name="shots_analyzer"
    # )

    # few_shot_prompt = []
    # for example in few_shots:
    #     few_shot_prompt.append(("human", example["input"]))
    #     few_shot_prompt.append(("ai", example["output"]))

    examples = load_prompt("prompts/analyze_user_question/fewshots.json")
    few_shot_prompt = []
    for example in examples:
        few_shot_prompt.append(("human", example["input"]))
        few_shot_prompt.append(("ai", example["output"]))

    ANALYZE_PROMPT = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            *few_shot_prompt,
            ("human", "사용자 질문: {user_question}"),
        ]
    )

    analyze_chain = ANALYZE_PROMPT | qwen_llm | output_parser
    analyzed_question = analyze_chain.invoke({"user_question": user_question})

    return analyzed_question


async def create_query(analyzed_question: str, today: str) -> str:
    """분석된 질문으로부터 SQL 쿼리를 생성
    Returns:
        str: 생성된 SQL 쿼리문
    Raises:
        ValueError: SQL 쿼리를 생성할 수 없거나, 추출 패턴이 매치되지 않는 경우
        TypeError: LLM 응답이 예상된 형식이 아닌 경우.
    """
    try:

        # table_name 추출: aicfo_get_cabo_2010[농협은행 잔고]에서 aicfo_get_cabo_2010만 추출
        table_name_pattern = r"aicfo_get_cabo_\d{4}"
        table_name = re.search(table_name_pattern, analyzed_question)[0]

        # refined_question 추출: aicfo_get_cabo_2010[농협은행 잔고] "농협은행 잔고"만 추출
        refined_question_pattern = r"\[(.*?)\]"
        refined_question = re.search(refined_question_pattern, analyzed_question).group(
            1
        )

        """
        프롬프트는 네 부분으로 구성됩니다.
        1) 시스템 프롬프트
        2) 스키마 프롬프트 (테이블의 칼럼명을 가져옵니다.)
        3) 퓨 샷
        4) 사용자 프롬프트 (오늘 날짜 및 분석된 질의)
        """
        system_prompt = load_prompt("prompts/create_query/system.prompt").format(
            today=today
        )
        schema_prompt = (
            f"테이블: {table_name}\n"
            + "칼럼명:\n"
            + load_prompt("prompts/create_query/schema.json")[table_name]
        )

        print("\n=== Few-shot Retrieval Process ===")
        # Extract year from table_name (e.g., "2011" from "aicfo_get_cabo_2011")
        back_number = re.search(r'\d{4}$', table_name).group()
        collection_name = f"shots_{back_number}"

        # retriever를 사용하여 동적으로 few-shot 예제 가져오기
        few_shots = await retriever.get_few_shots(
            query_text=refined_question,
            task_type="creator",
            collection_name=collection_name
        )

        few_shot_prompt = []
        for example in few_shots:
            few_shot_prompt.append(("human", example["input"]))
            few_shot_prompt.append(("ai", example["output"]))

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_prompt + schema_prompt),
                *few_shot_prompt,
                ("human", refined_question),
            ]
        )

        chain = prompt | qwen_llm

        # LLM 호출 및 출력 받기
        output = chain.invoke(
            {"refined_question": refined_question}
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
        print("\n=== Setting up DB Connection ===")
        parameters = {}
        execution_options = {}
        # db_path = os.getenv("DB_HOST")
        # print(f"Database path: {db_path}")

        # URL encode the password to handle special characters
        from urllib.parse import quote_plus
        password = quote_plus(str(Config.DB_PASSWORD))
        db_url = f"postgresql://{Config.DB_USER}:{password}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_DATABASE}"
        
        print("Creating database engine...")
        engine = create_engine(db_url)
        print("Engine created successfully")

        print("\n=== Executing Query ===")
        with engine.begin() as connection:
            print("Connection established")
            
            if isinstance(command, str):
                print("Converting string command to SQLAlchemy text...")
                command = text(command)
                print("Conversion successful")
            elif isinstance(command, Executable):
                print("Command is already SQLAlchemy executable")
            else:
                print(f"Invalid command type: {type(command)}")
                raise TypeError(f"Query expression has unknown type: {type(command)}")

            print("Executing command...")
            cursor = connection.execute(
                command,
                parameters,
                execution_options=execution_options,
            )
            print("Command executed successfully")

            if cursor.returns_rows:
                print("\n=== Processing Results ===")
                if fetch == "all":
                    print("Fetching all rows...")
                    rows = cursor.fetchall()
                    print(f"Retrieved {len(rows)} rows")
                    result = [x._asdict() for x in rows]
                    print("Converted rows to dictionaries")
                elif fetch == "one":
                    print("Fetching one row...")
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


def sql_response(user_question, sql_query, query_result_stats) -> str:
    """쿼리 실행 결과를 바탕으로 자연어 응답을 생성합니다.
    Returns:
        str: 생성된 자연어 응답.
    Raises:
        ValueError: 프롬프트 템플릿 로딩 실패 또는 LLM 응답 생성 실패시.
    """
    output_parser = StrOutputParser()

    system_prompt = load_prompt("prompts/sql_response/system.prompt").format(
        sql_query=sql_query, query_result_stats=query_result_stats
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            (
                "human",
                """사용자 질문: {user_question}""",
            ),
        ]
    )
    chain = prompt | qwen_llm | output_parser

    output = chain.invoke({"user_question": user_question})
    return output