import duckdb
from tools.helper_tools import text2sql_aggregate
import pandas as pd
from prompts.tool_prompts import (
    get_trsc_nl2sql_prompt,
    get_balance_nl2sql_prompt,
    get_past_balance_nl2sql_prompt,
    get_loan_trsc_nl2sql_prompt,
    get_loan_balance_nl2sql_prompt,
)
from llm_models.models import open_llm as llm


def clean_sql_query(query_string):
    query = query_string
    if "SQL:" in query:
        query = query.split("SQL:")[1]
    if "sql" in query.lower():
        query = query.split("sql")[1]
    lines = query.split("\n")
    # Remove line containing "질문:"
    filtered_lines = [line for line in lines if "질문:" not in line]
    query = "\n".join(filtered_lines)
    return query.strip("`").replace("`", "")


class GenericSQLQueryHandler:
    def __init__(
            self, llm, table_name, prompt_func, empty_response_func, process_results_func
    ):
        """
        llm: The language model object
        table_name: DuckDB에서 쿼리할 테이블 이름
        prompt_func: prompt.tool_prompts 모듈에 있는 프롬프트 함수
        empty_response_func: Dataframe이 비었을 경우 어떤 결과값을 줄 지 정해 둔 함수 -> (result_message, empty_df, calc_data)
        process_results_func: SQL로 처리한 데이터의 메타 데이터 및 최종 반환 값을 결정하는 함수 -> (result_message, processed_df, calc_data)
        """
        self.llm = llm
        self.table_name = table_name
        self.prompt_func = prompt_func
        self.empty_response_func = empty_response_func
        self.process_results_func = process_results_func

    def execute_query(self, input_str: str, source: str, dataframes: dict):
        try:
            print(f"Input Query: {input_str}")
            print(f"Source: {source}")

            df = dataframes[source]
            duckdb.register(self.table_name, df)

            # sql 실행 이후 필터링된 데이터프레임이 비어있을 경우의 예외 처리
            if len(df) == 0:
                return self.empty_response_func()

            # 프롬프트 생성 과정
            prompt = self.prompt_func(input_str)

            # 디버깅용으로 포매팅된 메시지 보기 ############################
            formatted_messages = prompt.format_messages(input=input_str)
            print("\nFormatted Prompt:")
            for message in formatted_messages:
                print(f"Role: {message.type}")
                print(f"Content: {message.content}\n")

            chain = prompt | self.llm
            print("\nSending to LLM...")
            response = chain.invoke({"input": input_str})
            print("\nLLM Response:")
            print(f"Response Type: {type(response)}")
            print(f"Response Content: {response}")

            sql_query = clean_sql_query(response)
            # sql_query = clean_sql_query(response.content)
            print(f"\nCleaned SQL Query: {sql_query}")

            try:
                df = duckdb.query(sql_query).to_df()
                return self.process_results_func(input_str, df)
            except KeyError as e:
                error_msg = f"KeyError: {str(e)}\n SQL Query:{sql_query}"
                return error_msg, None, None
            except Exception as e:
                error_msg = f"처리 중 오류가 발생했습니다: {str(e)}"
                return error_msg, None, None

        except Exception as e:
            print(f"Error in execute_query: {str(e)}")
            raise


# 잔액/거래내역 데이터의 반환값 관련 재사용 가능한 함수들
def empty_balance_response():
    return (
        "사용자의 질문에 해당하는 계좌는 총 0개이고, 잔액 총액은 0원입니다.",
        pd.DataFrame(),
        0,
    )


def process_balance_results(input_str: str, df: pd.DataFrame):
    count = len(df)
    try:
        total = df["REAL_AMT"].sum()
    except:
        total = text2sql_aggregate(input_str, df)
    result = f"사용자의 질문에 해당하는 데이터 건수는 총 {count} 개이고, 값은 {total}원입니다."
    calc_data = None
    if len(df) == 1:
        d = df.iloc[0].to_dict()
        calc_data = d[list(d)[0]]
    return result, df, calc_data


def empty_transaction_response():
    return (
        "사용자의 질문에 해당하는 거래는 총 0개이고, 잔액 총액은 0원입니다.",
        pd.DataFrame(),
        0,
    )


def process_transaction_results(input_str: str, df: pd.DataFrame):
    count = len(df)
    if 0 < count < 10:
        if "TRSC_DT" in df.columns:
            df["TRSC_DT"] = pd.to_datetime(df["TRSC_DT"], unit="ms").dt.strftime(
                "%Y-%m-%d"
            )
        result = f"사용자의 질문에 대해 해당하는 데이터는 {df.to_json(orient='records', force_ascii=False)}입니다."
        calc_data = df.iloc[0].to_dict()[list(df)[0]] if len(df.columns) > 0 else None
    else:
        result = f"사용자의 질문에 해당하는 데이터는 총 {count}건입니다."
        calc_data = None
    return result, df, calc_data


# 수시입출 잔액
balance_handler = GenericSQLQueryHandler(
    llm=llm,
    table_name="account_balances",
    prompt_func=get_balance_nl2sql_prompt,
    empty_response_func=empty_balance_response,
    process_results_func=process_balance_results,
)

# 수시입출 과거 잔액
balance_handler_past = GenericSQLQueryHandler(
    llm=llm,
    table_name="account_balances_past",
    prompt_func=get_past_balance_nl2sql_prompt,
    empty_response_func=empty_balance_response,
    process_results_func=process_balance_results,
)

# 수시입출 거래내역
transaction_handler = GenericSQLQueryHandler(
    llm=llm,
    table_name="bank_transactions",
    prompt_func=lambda input_str: get_trsc_nl2sql_prompt(task=input_str),
    empty_response_func=empty_transaction_response,
    process_results_func=process_transaction_results,
)

# 대출 잔액
loan_balance_handler = GenericSQLQueryHandler(
    llm=llm,
    table_name="loan_accounts",
    prompt_func=get_loan_balance_nl2sql_prompt,
    empty_response_func=empty_balance_response,  # same logic as normal balance, or create a new one if needed
    process_results_func=process_balance_results,  # same logic as normal balance, or create a new one if needed
)

# 대출 거래 내역
loan_transaction_handler = GenericSQLQueryHandler(
    llm=llm,
    table_name="loan_transactions",
    prompt_func=lambda input_str: get_loan_trsc_nl2sql_prompt(task=input_str),
    empty_response_func=empty_transaction_response,
    process_results_func=process_transaction_results,
)
