from datetime import datetime
from typing import TypedDict, Tuple, List, Dict
from xmlrpc.client import boolean

from api.dto import CompanyInfo
from graph.task.yadon import shellder
from graph.task.yadoran import yadoking
from graph.task.commander import command
from graph.task.nl2sql import create_sql
from graph.task.respondent import response
from graph.task.executor import execute
from graph.task.referral import question_referral
from graph.task.funk import func_select
from graph.task.nodata import no_data
from graph.task.params import parameters
from graph.task.killjoy import kill_joy

from llm_admin.state_manager import StateManager
from utils.logger import setup_logger
from utils.check_acct import check_acct_no
from utils.filter_com import filter_com
from utils.view_table import extract_view_date, add_view_table
from utils.orderby import add_order_by
from utils.modify_stock import modify_stock
from utils.is_krw import is_krw
from utils.extract_col import extract_col, transform_data
from utils.fff import fulfill_fstring

logger = setup_logger('node')

class ProcessingFlags(TypedDict):
    referral: List[str]
    residual_com: List[str]
    selected_com: str
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
    selected_api: str
    sql_query: str
    query_result_stats: str
    date_info: Tuple[str, str]
    query_result: dict
    final_answer: str
    flags: ProcessingFlags
    last_data: List[Dict[str, str]] # 이전 3개 그래프의 사용자 질문, 답변, SQL 쿼리
    
today = datetime.now().strftime("%Y-%m-%d")

async def yadon(state: GraphState) -> GraphState:
    """last_data 기반으로 질문을 검문하는 노드"""
    logger.info("yadon start")
    
    if state.get("last_data"):
        trace_id = state["trace_id"]
        user_question = state["user_question"]
        last_data = state["last_data"]

        shellder_result = await shellder(trace_id, user_question, last_data)
        
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

        new_question = await yadoking(trace_id, user_question, last_data, today)
        state["user_question"] = new_question
    logger.info("yadoran end")
    return state

async def commander(state: GraphState) -> GraphState:
    """사용자 질문에 검색해야 할 table을 선택
    Returns:
        GraphState: selected_table 업데이트.
    Raises:
        KeyError: state에 user_question이 없는 경우.
    """
    logger.info("commander start")
    user_question = state["user_question"]
    trace_id = state["trace_id"]
    
    selected_table = await command(trace_id, user_question)

    state.update({"selected_table": selected_table})
    
    StateManager.update_state(trace_id, {
        "user_question": user_question,
        "selected_table": selected_table
    })

    return state

async def funk(state: GraphState) -> GraphState:
    """사용자 질문에 검색해야 할 table을 선택
    Returns:
        GraphState: selected_table 업데이트.
    Raises:
        KeyError: state에 user_question이 없는 경우.
    """
    logger.info("funk start")
    user_question = state["user_question"]
    trace_id = state["trace_id"]

    selected_api = await func_select(trace_id, user_question)

    state.update({"selected_api": selected_api})

    logger.info("funk end")
    return state


async def params(state: GraphState) -> GraphState:
    """사용자 질문을 기반으로 SQL 쿼리를 생성(sql함수에 paramsa만 채워넣음)
    Returns:
        GraphState: sql_query가 추가된 상태.
    Raises:
        KeyError: state에 필요한 값이 없는 경우.
        ValueError: SQL 쿼리 생성에 실패한 경우.
    """
    logger.info("params start")
    trace_id = state["trace_id"]
    selected_api = state["selected_api"]
    user_question = state["user_question"]
    company_list = state["access_company_list"]
    main_com = company_list[0].custNm
    user_info = state["user_info"]

    # SQL 쿼리 생성
    sql_query, date_info = await parameters(
        trace_id, selected_api, user_question, main_com, user_info, today
    )

    # 상태 업데이트
    state.update(
        {
            "sql_query": sql_query,
            "date_info": date_info
        }
    )
    StateManager.update_state(trace_id, {"sql_query": sql_query})
    logger.info("params end")
    return state


async def nl2sql(state: GraphState) -> GraphState:
    """사용자 질문을 기반으로 SQL 쿼리를 생성(NL2SQL)
    Returns:
        GraphState: sql_query가 추가된 상태.
    Raises:
        KeyError: state에 필요한 값이 없는 경우.
        ValueError: SQL 쿼리 생성에 실패한 경우.
    """
    logger.info("nl2sql start")
    trace_id = state["trace_id"]
    selected_table = state["selected_table"]
    user_question = state["user_question"]
    company_list = state["access_company_list"]
    main_com = company_list[0].custNm
    sub_coms = [comp.custNm for comp in company_list[1:]]

    # SQL 쿼리 생성
    sql_query = await create_sql(trace_id, selected_table, user_question, main_com, sub_coms, today)
    # 상태 업데이트
    state.update({"sql_query": sql_query,})
    StateManager.update_state(trace_id, {"sql_query": sql_query})
    logger.info("nl2sql end")
    return state

def executor(state: GraphState) -> GraphState:
    """SQL 쿼리를 실행하고 결과를 분석
    Returns:
        GraphState: query_result와 query_result_stats가 추가된 상태.
    Raises:
        ValueError: SQL 쿼리가 state에 없거나 실행에 실패한 경우.
    """
    logger.info("executor start")
    trace_id = state["trace_id"]
    selected_table = state["selected_table"]
    
    if selected_table == "api":
        query = state.get("sql_query")
        result = execute(query)
    
    else:
        company_list = state["access_company_list"]
        main_com = company_list[0].custNm
        sub_coms = [comp.custNm for comp in company_list[1:]]
        
        raw_query = state.get("sql_query")
        if not raw_query:
            raise ValueError("SQL 쿼리가 state에 포함되어 있지 않습니다.")
        
        user_info = state.get("user_info")
        flags = state.get("flags")

        # 회사명을 권한 있는 회사로 변환. 이와 함께 권한 없는 조건, 회사 변환 조건이 처리됨
        query_one_com, residual_com, selected_com = filter_com(raw_query, main_com, sub_coms, flags)
        
        if selected_com:
            flags["residual_com"] = residual_com
            flags["selected_com"] = selected_com
        
        if flags["no_access"] == True:
            # CompanyInfo 객체들에서 회사명만 추출하여 리스트로 만듦
            accessible_companies = [comp.custNm for comp in company_list]
            # 회사명들을 쉼표와 공백으로 구분하여 하나의 문자열로 만듦
            companies_str = ", ".join(accessible_companies)
            
            state.update({
                "final_answer": f"해당 기업의 조회 권한이 없습니다. 조회 가능하신 기업은 {companies_str}입니다.",
                "query_result": [],
                "sql_query": ""
            })
        
        # stock 종목명 체크 맟 변환
        if selected_table == 'stock':
            query_one_com = modify_stock(query_one_com)

        # SELECT절에서 컬럼을 추출하고 그에 맞게 ORDER BY 추가
        query_ordered = add_order_by(query_one_com, selected_table)

        try:
            # 날짜를 추출하고, 미래 시제일 경우 변환
            view_date = extract_view_date(raw_query, selected_table, flags)
            # 뷰테이블 파라미터를 SQL 쿼리에 추가
            query = add_view_table(query_ordered, selected_table, user_info, view_date, flags)
            
            # 미래 시제를 오늘 날짜로 변경했다면 답변도 이를 반영하기 위해 user_question을 수정
            if flags.get("date_changed"):
                user_question = state["user_question"]
                state["user_question"] = f"{user_question}..아니다, 오늘 날짜 기준으로 해줘"
            
            result = execute(query)

        except Exception as e:
            logger.error(f"Error in view table processing: {str(e)}")
            result = execute(query_ordered)

    # 결과가 없는 경우 처리
    if not result:
        flags["no_data"] = True
        empty_result = []
        state.update({
            "query_result_stats": "nodata",
            "query_result": empty_result
        })
        StateManager.update_state(trace_id, {
            "query_result_stats": "nodata",
            "query_result": empty_result
        })
        logger.info("executor end")
        return state

    state.update({"query_result": result, "date_info": view_date})
    StateManager.update_state(trace_id, {"query_result": result})
    
    logger.info("executor end")
    return state

async def respondent(state: GraphState) -> GraphState:
    """쿼리 결과를 바탕으로 최종 응답을 생성"""
    logger.info("respondent start")
    trace_id = state["trace_id"]
    user_question = state["user_question"]
    result = state["query_result"]
    flags = state.get("flags")
    date_info = state["date_info"]
    
    raw_column_list = extract_col(result)
    logger.info(raw_column_list)
    result_for_col, column_list = transform_data(result, raw_column_list)
    logger.info(column_list)
    
    # 샷 제작용
    column_list_str = ", ".join(column_list)
    state.update({"query_result_stats": column_list_str})
    # 샷 제작용
    
    # SQL 쿼리 생성
    fstring_answer = await response(trace_id, user_question, column_list, date_info)
    final_answer = fulfill_fstring(fstring_answer, result_for_col, column_list)

    selected_table = state["selected_table"]
    final_result = check_acct_no(result, selected_table)
    if selected_table == "api":
        final_result = is_krw(final_result)
    state.update({"query_result": final_result})
    StateManager.update_state(trace_id, {"query_result": final_result})   
    
    # 날짜가 변경된 경우 안내 메시지 추가
    if flags.get("date_changed"):
        final_answer = "요청주신 시점은 제가 조회가 불가능한 시점이기에 오늘 날짜를 기준으로 조회했습니다. " + final_answer

    state.update({"final_answer": final_answer})
    StateManager.update_state(trace_id, {"final_answer": final_answer})
    logger.info("respondent end")
    return state

async def referral(state: GraphState) -> GraphState:
    """복수 사업장 중 하나만 조회했으니 다른 것도 조회할지 권유하는 노드"""
    logger.info("referral start")
    trace_id = state["trace_id"]
    user_question = state["user_question"]
    flags = state["flags"]

    # flags에서 selected_com과 residual_com 가져오기
    selected_com = flags.get("selected_com", "")
    residual_com = flags.get("residual_com", [])

    referral_list = await question_referral(
        trace_id=trace_id,
        user_question=user_question,
        selected_com=selected_com,
        residual_com=residual_com
    )

    flags["referral"] = referral_list
    logger.info("referral end")
    return state

async def nodata(state: GraphState) -> GraphState:
    """데이터가 없음을 설명하는 노드"""
    logger.info("nodata start")
    trace_id = state["trace_id"]
    user_question = state["user_question"]

    final_answer = await no_data(trace_id, user_question)

    state.update({"final_answer": final_answer})
    StateManager.update_state(trace_id, {"final_answer": final_answer})
    logger.info("nodata end")
    return state

async def killjoy(state: GraphState) -> GraphState:
    """장난하지 말고 재무 데이터나 물어보라는 노드"""
    logger.info("killjoy start")
    trace_id = state["trace_id"]
    user_question = state["user_question"]
    
    final_answer = await kill_joy(trace_id, user_question)
    
    state.update({
        "final_answer": final_answer,
        "query_result": [],
        "sql_query": "",
        "query_result_stats": ""
    })
    
    StateManager.update_state(trace_id, {"final_answer": final_answer})
    logger.info("killjoy end")
    return state