from datetime import datetime
from typing import TypedDict, Tuple, List, Dict
from xmlrpc.client import boolean

from api.dto import CompanyInfo
from graph.task.shellder import shellder
from graph.task.yadoking import yadoking
from graph.task.select_table import select_table
from graph.task.create_query import create_query
from graph.task.sql_response import sql_response
from graph.task.execute_query import execute_query
from graph.task.referral import question_referral
from graph.task.nodata import no_data
from utils.check_acct import check_acct_no
from utils.stats import calculate_stats
from utils.filter_com import filter_com
from utils.view_table import extract_view_date, add_view_table
from utils.orderby import add_order_by
from llm_admin.state_manager import StateManager
from utils.logger import setup_logger

logger = setup_logger('node')

class ProcessingFlags(TypedDict):
    referral: List[str]
    no_data: bool
    no_access: bool
    com_changed: bool
    date_changed: bool

class GraphState(TypedDict):
    chain_id: str
    trace_id: str
    user_info: Tuple[str, str]
    access_company_list: List[CompanyInfo]
    shellder: boolean
    user_question: str
    selected_table: str
    sql_query: str
    query_result_stats: str
    query_result: dict
    final_answer: str
    flags: ProcessingFlags
    last_data: List[Dict[str, str]] # 이전 3개 그래프의 사용자 질문, 답변, SQL 쿼리

async def yadon(state: GraphState) -> GraphState:
    """last_data 기반으로 질문을 검문하는 노드"""
    logger.info("yadon start")
    
    if state.get("last_data"):
        trace_id = state["trace_id"]
        user_question = state["user_question"]
        last_data = state["last_data"]

        shellder_result = await shellder(trace_id, user_question, last_data)
        
        # Handle the "no" case
        if shellder_result == "no":
            state.update({
                "final_answer": "금융 데이터 조회와 관련이 없는 질문으로 판단됩니다.",
                "query_result": [],
                "sql_query": "",
                "shellder": "no"
            })
        else:
            # Convert string "1" to True, "0" to False
            shellder_check = shellder_result == "1"
            state["shellder"] = shellder_check
    else:
        state["shellder"] = False
    
    logger.info("yadon end")
    return state

async def yadoran(state: GraphState) -> GraphState:
    """shellder가 True일 때 질문을 재해석하는 노드"""
    logger.info("yadoran start")
    if state["shellder"]:
        trace_id = state["trace_id"]
        user_question = state["user_question"]
        last_data = state["last_data"]

        new_question = await yadoking(trace_id, user_question, last_data)
        state["user_question"] = new_question
    logger.info("yadoran end")
    return state

async def table_selector(state: GraphState) -> GraphState:
    """사용자 질문에 검색해야 할 table을 선택
    Returns:
        GraphState: selected_table 업데이트.
    Raises:
        KeyError: state에 user_question이 없는 경우.
    """
    logger.info("table_selector start")
    user_question = state["user_question"]
    trace_id = state["trace_id"]
    
    selected_table = await select_table(trace_id, user_question)

    state.update({"selected_table": selected_table})

    if selected_table == "api":
        state.update({
            "final_answer": "이 질문은 api로 굉장히 멋있는 답변을 제공드릴 예정입니다.",
            "query_result": [],  # Empty list for raw_data
            "sql_query": "",
            "query_result_stats": "" # temporary 
        })
    
    StateManager.update_state(trace_id, {
        "user_question": user_question,
        "selected_table": selected_table,
        **({"final_answer": state["final_answer"], 
            "query_result": state["query_result"],
            "sql_query": state["sql_query"]} if selected_table == "api" else {})
    })

    return state


async def query_creator(state: GraphState) -> GraphState:
    """사용자 질문을 기반으로 SQL 쿼리를 생성(NL2SQL)
    Returns:
        GraphState: sql_query가 추가된 상태.
    Raises:
        KeyError: state에 필요한 값이 없는 경우.
        ValueError: SQL 쿼리 생성에 실패한 경우.
    """
    trace_id = state["trace_id"]
    selected_table = state["selected_table"]
    user_question = state["user_question"]
    company_list = state["access_company_list"]
    main_com = company_list[0].custNm
    sub_coms = [comp.custNm for comp in company_list[1:]]
    today = datetime.now().strftime("%Y-%m-%d")

    # SQL 쿼리 생성
    sql_query = await create_query(trace_id, selected_table, user_question, main_com, sub_coms, today)
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
    company_list = state["access_company_list"]
    main_com = company_list[0].custNm
    sub_coms = [comp.custNm for comp in company_list[1:]]
    raw_query = state.get("sql_query")
    if not raw_query:
        raise ValueError("SQL 쿼리가 state에 포함되어 있지 않습니다.")
    user_info = state.get("user_info")
    selected_table = state.get("selected_table")
    flags = state.get("flags")

    logger.info(f"flag0: {flags}")
    query_one_com, residual_com, selected_com = filter_com(raw_query, main_com, sub_coms, flags)
    
    if flags["no_access"] == True:
        state.update({
            "final_answer": "해당 기업의 조회 권한이 없습니다.",
            "query_result": [],
            "sql_query": ""
        })
    logger.info(f"flag1: {flags}")
    query_ordered = add_order_by(query_one_com, selected_table)

    try:
        view_date = extract_view_date(raw_query, selected_table, flags)
        query = add_view_table(query_ordered, selected_table, user_info, view_date, flags)
        logger.info(f"flag2: {flags}")
        logger.info(f"query-m: {query}")
        result = execute_query(query)

    except Exception as e:
        logger.error(f"Error in view table processing: {str(e)}")
        result = execute_query(query_ordered)

    # 결과가 없는 경우 처리
    if not result:
        flags["no_data"] = True
        logger.info(f"flag3: {flags}")
        empty_result = []
        state.update({
            "query_result_stats": "데이터가 없습니다.",
            "query_result": empty_result
        })
        StateManager.update_state(trace_id, {
            "query_result_stats": "데이터가 없습니다.",
            "query_result": empty_result
        })
        return state

    # 통계 계산
    query_result_stats = calculate_stats(result)

    # 계좌번호별 추가 그룹화
    final_result = check_acct_no(result, selected_table)

    # 상태 업데이트
    state.update({"query_result_stats": query_result_stats, "query_result": final_result})
    StateManager.update_state(trace_id, {"query_result_stats": query_result_stats, "query_result": final_result})
    
    return state

async def sql_respondent(state: GraphState) -> GraphState:
    """쿼리 결과를 바탕으로 최종 응답을 생성
    Returns:
        GraphState: final_answer가 추가된 상태.
    Raises:
        KeyError: (user_question, query_result_stats)가 없는 경우.
    """
    trace_id = state["trace_id"]
    user_question = state["user_question"]
    sql_query = state["sql_query"]
    query_result_stats = state.get("query_result_stats", [])

    # 결과가 없는 경우 처리
    if query_result_stats == []:
        final_answer = f'죄송합니다. 요청주신 내용에 따라 데이터베이스에서 다음 내용을 검색했지만 데이터가 없었습니다. \n {sql_query}'
        state.update({"final_answer": final_answer})
        return state
    
    output = await sql_response(
        trace_id,
        user_question=user_question,
        query_result_stats=query_result_stats
    )

    final_answer = (str(output))

    state.update({"final_answer": final_answer})
    StateManager.update_state(trace_id, {"final_answer": final_answer})
    return state

async def referral(state: GraphState) -> GraphState:
    """복수 사업장 중 하나만 조회했으니 다른 것도 조회할지 권유하는 노드"""
    logger.info("referral start")
    trace_id = state["trace_id"]
    user_question = state["user_question"]
    flags = state["flags"]

    referral_list = await question_referral(trace_id, user_question)

    flags["referral"] = referral_list
    logger.info("referral end")
    return state

async def nodata(state: GraphState) -> GraphState:
    """데이터가 없어서 사과드리는 노드"""
    logger.info("nodata start")
    trace_id = state["trace_id"]
    user_question = state["user_question"]

    final_answer = await no_data(trace_id, user_question)

    state.update({"final_answer": final_answer})
    StateManager.update_state(trace_id, {"final_answer": final_answer})
    logger.info("nodata end")
    return state