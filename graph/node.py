from typing import TypedDict
from .task import analyze_user_question, create_query, sql_response, execute_query
from datetime import datetime
from .utils import analyze_data


class GraphState(TypedDict):
    user_question: str  # 최초 사용자 질의
    analyzed_question: str  # analyzer를 통해 분석된 질의
    sql_query: str  # NL2SQL을 통해 생성된 SQL 쿼리
    query_result_stats: (
        str  # sql_query 실행 결과에 따른 데이터의 통계값 (final_answer 생성에 사용)
    )
    query_result: dict  # sql_query 실행 결과 데이터 (데이터프레임 형식)
    final_answer: str  # 최종 답변


########################### 정의된 노드 ###########################


def question_analyzer(state: GraphState) -> GraphState:
    print(f"Received user question: {state['user_question']}")
    
    user_question = state["user_question"]
    # analyzed_question = analyze_user_question(user_question)
    analyzed_question = "aicfo_get_cabo_2011[24년 국민은행 거래]"

    print(f"Analyzed question: {analyzed_question}")
    state.update({"analyzed_question": analyzed_question})
    return state


async def query_creator(state: GraphState) -> GraphState:
    """
    사용자 질문을 기반으로 SQL 쿼리를 생성하고 상태를 업데이트하는 노드.

    Args:
        state (GraphState): 그래프 상태

    Returns:
        GraphState: 업데이트된 그래프 상태
    """    
    analyzed_question = state["analyzed_question"]
    today = datetime.now().strftime("%Y-%m-%d")

    # SQL 쿼리 생성
    sql_query = await create_query(analyzed_question, today)
    print(f"SQL query created: {sql_query}")
    # 상태 업데이트
    state.update(
        {
            "sql_query": sql_query,
        }
    )
    return state


def result_executor(state: GraphState) -> GraphState:
    # SQL 쿼리 가져오기
    query = state.get("sql_query")
    if not query:
        raise ValueError("SQL 쿼리가 state에 포함되어 있지 않습니다.")

    # DB 쿼리 실행
    result = execute_query(query)

    # 결과가 None인 경우 빈 리스트로 초기화
    if result is None:
        result = {"columns": [], "rows": []}

        # 통계값 추출
    query_result_stats = analyze_data(result)

    # 상태 업데이트
    state.update({"query_result_stats": query_result_stats, "query_result": result})
    return state


def sql_respondent(state: GraphState) -> GraphState:
    user_question = state["user_question"]
    sql_query = state["sql_query"]
    query_result_stats = state.get("query_result_stats", [])
    final_answer = sql_response(
        user_question=user_question,
        sql_query=sql_query,
        query_result_stats=query_result_stats,
    )

    state.update({"final_answer": final_answer})
    return state