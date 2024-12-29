from langchain_core.prompts import ChatPromptTemplate
import duckdb
from llm_models.models import open_llm as llm


# nl2sql 툴이 기존의 table 스키마를 변경했을 경우 Evidence row에 합계 값을 넣기 위해 사용할 합계 도출 용 nl2sql 툴
def text2sql_aggregate(text, df):
    if not hasattr(df, "columns"):
        raise ValueError("The provided df is not a valid DataFrame")

    columns = df.columns.tolist()
    input = text

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
            너는 금융 관련 duckDB 전문가야.
            SQL을 활용해서, 사용자 질문과 column을 참고해서 해당 df에서 가장 대표적인 값 1개만 추출해.
            평균/합계 중 1개를 선택해서, 대표적인 값 1개만 추출해. 명심해, 열 1개, 행 1개여야 해. (질문에서 "은행별"이라고 해도, 전체 값을 대표하는 평균/합 중 하나를 선택해서 1개의 값만 추출해야 해.)
            SQL문만 보여주고 다른 설명은 모두 지워줘.
            테이블 명은 df이고, 칼럼은 Columns: [칼럼1, 칼럼2...]에 제시된 칼럼만 써야 해.

            예시:
            질문: "총 거래 내역은?"
            Columns: [SUM(TRSC_AMT)]
            SQL: SELECT SUM(TRSC_AMT) FROM df

            질문: "은행별 가중 평균 금리를 계산해줘"
            Columns: ['BANK_CD', 'WEIGHTED_AVG_RATE', 'SUM_CNTRCT_AMT']
            SQL: SELECT SUM(WEIGHTED_AVG_RATE * SUM_CNTRCT_AMT) / SUM(SUM_CNTRCT_AMT) AS WEIGHTED_AVG_RATE FROM df

            """,
            ),
            (
                "human",
                """
             질문: {input}
             Columns: {columns}
             SQL:
             """,
            ),
        ]
    )

    chain = prompt | llm

    response = chain.invoke({"input": input, "columns": columns})

    result_df = duckdb.query(response.content.strip("`")).to_df()

    result = result_df[list(result_df)[0]].item()

    return result
