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


def create_query(analyzed_question: str, today: str) -> str:
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
        examples = load_prompt("prompts/create_query/fewshots.json")

        few_shot_prompt = []
        for example in examples:
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
    parameters = {}
    execution_options = {}
    db_path = os.getenv("DATA_DB")
    engine = create_engine(db_path)

    with engine.begin() as connection:
        if isinstance(command, str):
            command = text(command)
        elif isinstance(command, Executable):
            pass
        else:
            raise TypeError(f"Query expression has unknown type: {type(command)}")

        cursor = connection.execute(
            command,
            parameters,
            execution_options=execution_options,
        )
        if cursor.returns_rows:
            if fetch == "all":
                result = [x._asdict() for x in cursor.fetchall()]
            elif fetch == "one":
                first_result = cursor.fetchone()
                result = [] if first_result is None else [first_result._asdict()]
            elif fetch == "cursor":
                return cursor
            else:
                raise ValueError(
                    "Fetch parameter must be either 'one', 'all', or 'cursor'"
                )

            return result


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
