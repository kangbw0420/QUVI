from datetime import datetime, timedelta
from typing import TypedDict, Tuple, List

from api.dto import CompanyInfo
from llm_admin.state_manager import StateManager
# from graph.task.yadon import shellder
# from graph.task.yadoran import yadoking
from graph.task.checkpoint import check_joy # from graph.classifier import check_joy
from graph.task.commander import command
from graph.task.nl2sql import create_sql
from graph.task.respondent import response
from graph.task.executor import execute
from graph.task.funk import func_select
from graph.task.nodata import no_data
from graph.task.params import parameters
from graph.task.killjoy import kill_joy

from utils.logger import setup_logger
from utils.extract_data_info import extract_col_from_query, extract_col_from_dict 
from utils.dataframe.final_format import final_format
from utils.query.filter_com import add_com_condition
from utils.query.check_viewdv import check_view_dv, is_all_view_dv
from utils.query.view.view_table import add_view_table
from utils.query.view.extract_date import extract_view_date
from utils.query.orderby import add_order_by
from utils.query.modify_name import modify_stock, modify_bank
from utils.dataframe.is_inout_krw import is_krw
from utils.dataframe.transform_col import transform_data
from utils.compute.main_compute import compute_fstring

logger = setup_logger('node')

class ProcessingFlags(TypedDict):
    is_joy: bool
    no_data: bool
    stock_sec: bool
    future_date: bool
    past_date: bool
    
class GraphState(TypedDict):
    chain_id: str
    trace_id: str
    user_info: Tuple[str, str]
    access_company_list: List[CompanyInfo]
    yogeumjae: str
    # shellder: boolean
    user_question: str
    selected_table: str
    selected_api: str
    sql_query: str
    column_list: List[str]
    date_info: Tuple[str, str]
    query_result: dict
    final_answer: str
    flags: ProcessingFlags
    # last_data: List[Dict[str, str]] # 이전 3개 그래프의 사용자 질문, 답변, SQL 쿼리
    
today = datetime.now().strftime("%Y-%m-%d")

# async def yadon(state: GraphState) -> GraphState:
#     """last_data 기반으로 질문을 검문하는 노드"""
#     if state.get("last_data"):
#         trace_id = state["trace_id"]
#         user_question = state["user_question"]
#         last_data = state["last_data"]
#         shellder_result = await shellder(trace_id, user_question, last_data)
#         shellder_check = shellder_result == "1"
#         state["shellder"] = shellder_check
#     else:
#         state["shellder"] = False    
#     return state

# async def yadoran(state: GraphState) -> GraphState:
#     """shellder가 True일 때 질문을 재해석하는 노드"""
#     if state["shellder"]:
#         trace_id = state["trace_id"]
#         user_question = state["user_question"]
#         last_data = state["last_data"]
#         new_question = await yadoking(trace_id, user_question, last_data, today)
#         state["user_question"] = new_question
#     return state

async def checkpoint(state: GraphState) -> GraphState:
    """금융 관련 질의 fin과 쓸데없는 질의 joy의 임베딩 모델 활용 이진분류"""
    user_question = state["user_question"]
    trace_id = state["trace_id"]
    flags = state.get("flags")

    is_joy = await check_joy(user_question)
    if is_joy['checkpoint'] == 'joy':
        flags["is_joy"] = True
        state.update({"selected_table": ""})
    
    StateManager.update_state(
        trace_id, 
        {
            "user_question": user_question
        }
    )

    return state

async def commander(state: GraphState) -> GraphState:
    """사용자 질문에 검색해야 할 table을 선택"""
    user_question = state["user_question"]
    trace_id = state["trace_id"]

    selected_table = await command(trace_id, user_question)

    yogeumjae = state["yogeumjae"]
    if selected_table == 'stock' and yogeumjae in ['muryo', 'stock0']:
        flags = state.get("flags")
        flags["stock_sec"] = True
        state.update({
        "selected_table": selected_table,
        "final_answer": "해당 질문은 증권 잔고 관련 질문으로 판단되었습니다. 접속하신 계정은 증권 잔고 데이터의 조회 권한이 없습니다.\n결제 후 모든 계좌의 데이터를 조회하실 수 있습니다.\U0001F64F\U0001F64F",
        "query_result": [],
        "sql_query": "",
        "column_list": []
    })
    else:
        state.update({"selected_table": selected_table})
    
    StateManager.update_state(trace_id, {
        "user_question": user_question,
        "selected_table": selected_table
    })

    return state

async def funk(state: GraphState) -> GraphState:
    """사용자 질문에 검색해야 할 table을 선택"""
    user_question = state["user_question"]
    trace_id = state["trace_id"]

    selected_api = await func_select(trace_id, user_question)

    state.update({"selected_api": selected_api})

    return state

async def params(state: GraphState) -> GraphState:
    """사용자 질문을 기반으로 SQL 쿼리를 생성(sql함수에 paramsa만 채워넣음)
    Raises:
        KeyError: state에 필요한 값이 없는 경우.
        ValueError: SQL 쿼리 생성에 실패한 경우.
    """
    trace_id = state["trace_id"]
    selected_api = state["selected_api"]
    user_question = state["user_question"]
    company_list = state["access_company_list"]
    main_companies = [comp for comp in company_list if comp.isMainYn == 'Y']
    if main_companies:
        main_com = main_companies[0].custNm
    else:
        main_com = company_list[0].custNm
    user_info = state["user_info"]
    flags = state.get("flags")
    yogeumjae = state["yogeumjae"]

    sql_query, date_info = await parameters(
        trace_id, selected_api, user_question, main_com, user_info, today, yogeumjae, flags
    )

    state.update({"sql_query": sql_query, "date_info": date_info})
    StateManager.update_state(trace_id, {"sql_query": sql_query})
    return state

async def nl2sql(state: GraphState) -> GraphState:
    """사용자 질문을 기반으로 SQL 쿼리를 생성(NL2SQL)
    Raises:
        KeyError: state에 필요한 값이 없는 경우.
        ValueError: SQL 쿼리 생성에 실패한 경우.
    """
    trace_id = state["trace_id"]
    selected_table = state["selected_table"]
    user_question = state["user_question"]
    company_list = state["access_company_list"]
    main_companies = [comp for comp in company_list if comp.isMainYn == 'Y']
    if main_companies:
        main_com = main_companies[0].custNm
    else:
        main_com = company_list[0].custNm

    sql_query = await create_sql(trace_id, selected_table, main_com, user_question, today)
    
    yogeumjae = state["yogeumjae"]
    view_dv_list = check_view_dv(sql_query)
    if ("증권" in view_dv_list and 
        yogeumjae in ['muryo', 'stock0'] and 
        not is_all_view_dv(view_dv_list)):
        flags = state.get("flags")
        flags["stock_sec"] = True
        state.update({
        "final_answer": "해당 질문은 증권 잔고 관련 질문으로 판단되었습니다. 접속하신 계정은 증권 잔고 데이터의 조회 권한이 없습니다.\n결제 후 모든 계좌의 데이터를 조회하실 수 있습니다.\U0001F64F\U0001F64F",
        "query_result": [],
        "column_list": []
    })

    state.update({"sql_query": sql_query,})
    StateManager.update_state(trace_id, {"sql_query": sql_query})
    return state

def executor(state: GraphState) -> GraphState:
    """SQL 쿼리를 실행하고 결과를 분석
    Raises:
        ValueError: SQL 쿼리가 state에 없거나 실행에 실패한 경우.
    """
    trace_id = state["trace_id"]
    selected_table = state["selected_table"]
    
    if selected_table == "api":
        query = state.get("sql_query")
        print("#" * 80)
        print(query)
        result = execute(query)
        if result:
            column_list = extract_col_from_dict(result)
        else:
            # nodata로 가기 전에 flags 참조
            flags = state.get("flags")
    
    else:
        raw_query = state.get("sql_query")
        if not raw_query:
            raise ValueError("SQL 쿼리가 state에 포함되어 있지 않습니다.")
        
        # 쿼리 길어지기 전에 컬럼부터 추출
        column_list = extract_col_from_query(raw_query)
        
        company_list = state["access_company_list"]
        main_companies = [comp for comp in company_list if comp.isMainYn == 'Y']
        if main_companies:
            main_com = main_companies[0].custNm
        else:
            main_com = company_list[0].custNm
        # 회사명을 권한 있는 회사로 변환. 이와 함께 권한 없는 조건, 회사 변환 조건이 처리됨
        query_com = add_com_condition(raw_query, main_com)

        # stock 종목명 체크 맟 변환
        if selected_table == 'stock':
            query_com = modify_stock(query_com)
        
        query_right_bank = modify_bank(query_com)
        query_ordered = add_order_by(query_right_bank, selected_table)
        
        user_info = state.get("user_info")
        flags = state.get("flags")
        try:
            # 날짜를 추출하고, 미래 시제일 경우 변환
            view_date = extract_view_date(raw_query, selected_table, flags)
            # 무료 유저가 감히 과거 데이터를 보려 했는지 검증
            yogeumjae = state["yogeumjae"]
            if yogeumjae == 'muryo':
                start_date = view_date[0]
                # 날짜 문자열을 datetime 객체로 변환
                start_date_dt = datetime.strptime(start_date, "%Y%m%d")
                today_dt = datetime.now().strptime(today, "%Y-%m-%d")
                
                # 날짜 차이 계산 (today - start_date)
                date_diff = today_dt - start_date_dt
                
                # start_date가 오늘보다 2일 이상 이전인 경우
                if date_diff.days >= 2:
                    yesterday = today_dt - timedelta(days=1)
                    # 날짜 형식을 YYYYMMDD로 변환
                    new_start_date = yesterday.strftime("%Y%m%d")
                    view_date = (new_start_date, view_date[1])
                    flags["past_date"] = True
            
            # 뷰테이블 파라미터를 SQL 쿼리에 추가
            query = add_view_table(query_ordered, selected_table, main_com, user_info, view_date, flags)
            
            # 미래 시제를 오늘 날짜로 변경했다면 답변도 이를 반영하기 위해 user_question을 수정
            if flags.get("future_date"):
                user_question = state["user_question"]
                state["user_question"] = f"{user_question}..아니다, 오늘 날짜 기준으로 해줘"
            
            if flags.get("past_date"):
                user_question = state["user_question"]
                state["user_question"] = f"{user_question}..아 잘못 알았다 어제로 보여줘"
            
            print("#" * 80)
            print(query)
            result = execute(query)
            state.update({"date_info": view_date})

        except Exception as e:
            logger.error(f"Error in view table processing: {str(e)}")
            result = execute(query_ordered)

    # 결과가 없는 경우 처리
    if not result:
        flags["no_data"] = True
        empty_result = []
        column_list = []
        state.update({"query_result": empty_result, "column_list": column_list})
        StateManager.update_state(trace_id, {"query_result": empty_result})
        
        return state
    
    state.update({"query_result": result, "column_list": column_list})
    StateManager.update_state(trace_id, {"query_result": result})
    
    return state

async def respondent(state: GraphState) -> GraphState:
    """쿼리 결과를 바탕으로 최종 응답을 생성"""
    trace_id = state["trace_id"]
    user_question = state["user_question"]
    result = state["query_result"]
    flags = state.get("flags")
    selected_table = state["selected_table"]
    raw_column_list = state["column_list"]

    # 컬럼과 데이터에서 입출금과 통화 구분
    result_for_col, column_list = transform_data(result, raw_column_list)
    
    # SQL 쿼리 생성
    if selected_table == "api":
        date_info = state["date_info"]
    else:
        date_info = ()
    fstring_answer = await response(trace_id, user_question, column_list, date_info)
    #debuging
    state.update({"yogeumjae": fstring_answer})
    #debuging
    final_answer = compute_fstring(fstring_answer, result_for_col, column_list)

    # result_inout = is_inout(result)
    final_result = final_format(result, selected_table)
    if selected_table == "api":
        final_result = is_krw(final_result)
    
    if flags.get("future_date"):
        final_answer = "요청주신 시점은 제가 조회가 불가능한 시점이기에 오늘 날짜를 기준으로 조회했습니다. " + final_answer
        
    if flags.get("past_date"):
        final_answer = final_answer + "\n\n해당 계정은 무료 계정이므로 2일 이전 데이터에 대해서는 조회 제한이 적용된 상황입니다.\n결제 후 모든 기간의 데이터를 조회하실 수 있습니다.\U0001F64F\U0001F64F"

    state.update({"final_answer": final_answer, "column_list": column_list, "query_result": final_result})
    StateManager.update_state(trace_id, {"final_answer": final_answer, "query_result": final_result})
    return state

async def nodata(state: GraphState) -> GraphState:
    """데이터가 없음을 설명하는 노드"""
    trace_id = state["trace_id"]
    user_question = state["user_question"]
    flags = state.get("flags")

    final_answer = await no_data(trace_id, user_question)

    if flags.get("future_date"):
        final_answer = "요청주신 시점은 제가 조회가 불가능한 시점이기에 오늘 날짜를 기준으로 조회했습니다. " + final_answer
        
    if flags.get("past_date"):
        final_answer = final_answer + "\n\n해당 계정은 무료 계정이므로 2일 이전 데이터에 대해서는 조회 제한이 적용된 상황입니다.\n결제 후 모든 기간의 데이터를 조회하실 수 있습니다.\U0001F64F\U0001F64F"

    state.update({"final_answer": final_answer})
    StateManager.update_state(trace_id, {"final_answer": final_answer})
    return state

async def killjoy(state: GraphState) -> GraphState:
    """장난하지 말고 재무 데이터나 물어보라는 노드"""
    trace_id = state["trace_id"]
    user_question = state["user_question"]
    
    final_answer = await kill_joy(trace_id, user_question)
    
    state.update({
        "final_answer": final_answer,
        "query_result": [],
        "sql_query": "",
        "column_list": []
    })
    
    StateManager.update_state(trace_id, {"final_answer": final_answer})
    return state