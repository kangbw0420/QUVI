from typing import TypedDict, Dict, Any
from .task import (
    analyze_user_question,
    create_query,
    sql_response,
    execute_query,
    select_table,
    columns_filter
)
from datetime import datetime
from .utils import analyze_data
from llm_admin.state_manager import StateManager


class GraphState(TypedDict):
    chain_id: str
    trace_id: str
    user_question: str  # 최초 사용자 질의
    selected_table: str  # 사용자 질의에 대한 선택된 테이블
    analyzed_question: str  # analyzer를 통해 분석된 질의
    sql_query: str  # NL2SQL을 통해 생성된 SQL 쿼리
    query_result_stats: (
        str  # sql_query 실행 결과에 따른 데이터의 통계값 (final_answer 생성에 사용)
    )
    query_result: dict  # sql_query 실행 결과 데이터 (데이터프레임 형식)
    final_answer: str  # 최종 답변
    last_data: list     # 이전 3개 그래프의 사용자 질문, 답변, SQL 쿼리
    

async def table_selector(state: GraphState) -> GraphState:
    """사용자 질문에 검색해야 할 table을 선택
    Returns:
        GraphState: selected_table 업데이트.
    Raises:
        KeyError: state에 user_question이 없는 경우.
    """
    user_question = state["user_question"]
    trace_id = state["trace_id"]
    
    # last_data 존재 검증은 try-except문으로 수행
    try:
        last_data = ''
        for x in state['last_data']:
            last_template = "\n당신이 참고할 수 있는 앞선 대화의 내용입니다."+\
                    f"\n- 이전 질문\n{x[0]}"+\
                    f"\n- 이전 질문에 대한 SQL쿼리\n{x[2]}"+\
                    f"\n- 이전 질문에 대한 답변\n{x[1]}\n"
            last_data += last_template

        selected_table = await select_table(trace_id, user_question, last_data)
    except KeyError:
        selected_table = await select_table(trace_id, user_question)

    state.update({"selected_table": selected_table})
    StateManager.update_state(trace_id, {"user_question": user_question, "selected_table": selected_table})

    return state


async def question_analyzer(state: GraphState) -> GraphState:
    """사용자 질문을 분석하여 간소화(개떡같은 질문을 찰떡같은 질문으로)
    Returns:
        GraphState: analyzed_question이 추가된 상태.
    Raises:
        KeyError: state에 user_question이 없는 경우.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    trace_id = state["trace_id"]
    # last_data 존재 검증은 try-except문으로 수행
    try:
        last_data = '\n*Context'
        
        for x in state['last_data']:
            last_template = f"\n**이전 질문\n- {x[0]}"#+\
                    # f"\n**이전 질문에 대한 SQL쿼리\n- {x[2]}"+\
                    # f"\n**이전 질문에 대한 답변\n- {x[1]}"
            last_data += last_template
        
        analyzed_question = await analyze_user_question(
            trace_id,
            state["user_question"], 
            state["selected_table"], 
            last_data,
            today
            )

    except KeyError:
        analyzed_question = await analyze_user_question(trace_id, state["user_question"], state["selected_table"], today)

    state.update({"analyzed_question": analyzed_question})
    StateManager.update_state(trace_id, {"analyzed_question": analyzed_question})

    return state

async def query_creator(state: GraphState) -> GraphState:
    """사용자 질문을 기반으로 SQL 쿼리를 생성(NL2SQL)
    Returns:
        GraphState: sql_query가 추가된 상태.
    Raises:
        KeyError: state에 analyzed_question이 없는 경우.
        ValueError: SQL 쿼리 생성에 실패한 경우.
    """
    trace_id = state["trace_id"]
    selected_table = state["selected_table"]
    analyzed_question = state["analyzed_question"]
    today = datetime.now().strftime("%Y-%m-%d")

    # SQL 쿼리 생성
    sql_query = await create_query(trace_id, selected_table, analyzed_question, today)
    # 상태 업데이트
    state.update({"sql_query": sql_query,})
    StateManager.update_state(trace_id, {"sql_query": sql_query})
    return state

def result_executor(state: GraphState) -> GraphState:
    """SQL 쿼리를 실행하고 결과를 분석
    Returns:
        GraphState: query_result와 query_result_stats가 추가된 상태.
    Raises:
        ValueError: SQL 쿼리가 state에 없거나 실행에 실패한 경우.
    """
    trace_id = state["trace_id"]
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
    else:
        if len(result)==0:
            query_result_stats = analyze_data(result)
        else:
            # 통계값 추출
            query_result_stats = analyze_data(result)
            # 컬럼 필터 result
            result = columns_filter(result, state["selected_table"])

    # 상태 업데이트
    state.update({"query_result_stats": query_result_stats, "query_result": result})
    StateManager.update_state(trace_id, {"query_result_stats": query_result_stats, "query_result": result})
    
    return state

def sql_respondent(state: GraphState) -> GraphState:
    """쿼리 결과를 바탕으로 최종 응답을 생성
    Returns:
        GraphState: final_answer가 추가된 상태.
    Raises:
        KeyError: (user_question, query_result_stats)가 없는 경우.
    """
    trace_id = state["trace_id"]
    user_question = state["user_question"]
    analyzed_question = state["analyzed_question"]
    query_result = state["query_result"]    # row가 5개 이하?
    query_result_stats = state.get("query_result_stats", [])

    # 결과가 없는 경우 처리
    if query_result_stats == {"숫자형 칼럼": {}, "범주형 칼럼": {}}:
        final_answer = f'죄송합니다. 요청주신 내용에 따라 데이터베이스에서 다음 내용을 검색했지만 데이터가 없었습니다.: {analyzed_question}'
        state.update({"final_answer": final_answer})
        return state
    
    output = sql_response(
        trace_id,
        user_question=user_question,
        query_result_stats=query_result_stats
    )

    # if len(query_result) < 6:
    #     output = sql_response(
            # trace_id, 
    #         user_question=user_question,
    #         query_result = query_result
    #     )
    # else:
    #     output = sql_response(
            # trace_id, 
    #         user_question=user_question,
    #         query_result_stats=query_result_stats
    #     )

    final_answer = (str(output))

    state.update({"final_answer": final_answer})
    StateManager.update_state(trace_id, {"final_answer": final_answer})
    return state