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
    output_parser = StrOutputParser()

    """
        프롬프트는 세 부분으로 구성됩니다.
        1) 시스템 프롬프트
        2) 퓨 샷
        3) 사용자 프롬프트 (사용자의 질문만)
        
    """
    system_prompt = load_prompt("prompts/analyze_user_question/system.prompt")
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
    """
    Args:
        analyzed_question (str): 사용자의 질문.
        today (str): 오늘 날짜

    Returns:
        str: 생성된 SQL 쿼리.
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
    """
    Executes SQL command through underlying engine.

    If the statement returns no rows, an empty list is returned.
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