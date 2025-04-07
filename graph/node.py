from llm_admin.state_manager import StateManager
from graph.types import GraphState
from graph.task.classifier import check_joy, is_api, classify_yqmd
from graph.task.commander import command
from graph.task.nl2sql import create_sql
from graph.task.table_respondent import response
from graph.task.executor import execute
from graph.task.funk import func_select
from graph.task.nodata import no_data
from graph.task.params import parameters
from graph.task.killjoy import kill_joy
from graph.task.safeguard import guard_query

from utils.logger import setup_logger
from utils.common.extract_data_info import extract_col_from_query, extract_col_from_dict
from utils.common.date_checker import check_date, correct_date_range
from utils.dataframe.format_df import delete_useless_col, final_df_format
from utils.query.filter_com import add_com_condition
from utils.query.view.view_table import view_table
from utils.query.orderby import add_order_by
from utils.query.modify_name import modify_stock, modify_bank
from utils.query.ever_note import ever_note
from utils.dataframe.is_krw_null import is_krw, is_null_only
<<<<<<< HEAD
from utils.dataframe.transform_col import transform_data
from utils.compute.main_compute import compute_fstring
from utils.table.main_table import evaluate_pandas_expression, evaluate_fstring_template
=======
>>>>>>> 8292a449b13105bb184be1f43288118e8dac8897

# 모듈 레벨 로거 생성
logger = setup_logger('node')


async def checkpoint(state: GraphState) -> GraphState:
    """금융 관련 질의 fin과 쓸데없는 질의 joy의 임베딩 모델 활용 이진분류"""
    user_question = state["user_question"]
    trace_id = state["trace_id"]
    flags = state.get("flags")

    is_joy = await check_joy(user_question)
    if is_joy['checkpoint'] == 'joy':
        flags["is_joy"] = True
        state.update({"selected_table": ""})

    StateManager.update_state(trace_id, {"user_question": user_question})
    return state

async def isapi(state: GraphState) -> GraphState:
    """사용자 질문을 api로 처리할 수 있을지 판단"""
    user_question = state["user_question"]
    trace_id = state["trace_id"]

    selected_table = await is_api(user_question)

    state.update({"selected_table": selected_table})
    StateManager.update_state(trace_id, {
        "user_question": user_question,
        "selected_table": selected_table
    })
    return state

async def commander(state: GraphState) -> GraphState:
    """사용자 질문에 검색해야 할 table을 선택"""
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
    company_id = state["company_id"]
    user_info = state["user_info"]
    flags = state.get("flags")

    sql_query, date_info = await parameters(
        trace_id, selected_api, user_question, company_id, user_info
    )

    # 날짜 교정: 유효하지 않은 날짜를 가장 가까운 유효한 날짜로 교정
    corrected_date_info = correct_date_range(date_info)
    date_info = corrected_date_info

    invalid_date_message = check_date(date_info, flags)
    if invalid_date_message:
        state.update({
            "final_answer": invalid_date_message,
            "query_result": [],
            "column_list": []
        })

    state.update({"sql_query": sql_query, "date_info": date_info})
    StateManager.update_state(trace_id, {
        "company_id": company_id,
        "sql_query": sql_query
    })
    return state

async def yqmd(state: GraphState) -> GraphState:
    """자금 흐름 api에서 연간/분기간/월간/일간 파라미터 결정"""
    user_question = state["user_question"]
    sql_query = state["sql_query"]

    query_yqmd = await classify_yqmd(user_question, sql_query)
    state.update({"sql_query": query_yqmd})

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
    company_id = state["company_id"]

    sql_query = await create_sql(trace_id, selected_table, company_id, user_question)

    state.update({"sql_query": sql_query,})
    StateManager.update_state(trace_id, {
        "company_id": company_id,
        "sql_query": sql_query
    })
    return state

async def executor(state: GraphState) -> GraphState:
    """SQL 쿼리를 실행하고 결과를 분석
    Raises:
        ValueError: SQL 쿼리가 state에 없거나 실행에 실패한 경우.
    """
    trace_id = state["trace_id"]
    selected_table = state["selected_table"]
    flags = state.get("flags")

    if "safe_count" not in flags:
        flags["safe_count"] = 0

    if selected_table == "api":
        query = state.get("sql_query")
        logger.info(f"Executing API query: {query}")
        try:
            result = execute(query)
            state.update({"sql_query": query})
            if result:
                column_list = extract_col_from_dict(result)
            else:
                # nodata로 가기 전에 flags 참조
                flags["no_data"] = True
        except Exception as e:
            raise
    
    else:
        raw_query = state.get("sql_query")
        if not raw_query:
            logger.error("No SQL query in state")
            raise ValueError("SQL 쿼리가 state에 포함되어 있지 않습니다.")

        # 쿼리 길어지기 전에 컬럼부터 추출
        column_list = extract_col_from_query(raw_query)
        
        company_id = state["company_id"]

        # 회사명을 권한 있는 회사로 변환
        query_com = add_com_condition(raw_query, company_id)

        # stock 종목명 체크 맟 변환
        if selected_table == 'stock':
            query_com = modify_stock(query_com)
        
        query_right_bank = modify_bank(query_com)
        query_ordered = add_order_by(query_right_bank, selected_table)
        
        user_info = state.get("user_info")
        flags = state.get("flags")
        try:
            # 날짜를 추출하고, 미래 시제일 경우 변환
            query, view_dates = view_table(query_ordered, selected_table, company_id, user_info, flags)
            
            if 'main' in view_dates:
                # 날짜 교정: 유효하지 않은 날짜를 가장 가까운 유효한 날짜로 교정
                corrected_date_info = correct_date_range(view_dates['main'])
                view_dates['main'] = corrected_date_info
                
                # 유효성 검사 후 처리
                invalid_date_message = check_date(view_dates['main'], flags)
                if invalid_date_message:
                    state.update({
                        "final_answer": invalid_date_message,
                        "query_result": [],
                        "column_list": []
                    })
                    return state

            # 미래 시제를 오늘 날짜로 변경했다면 답변도 이를 반영하기 위해 user_question을 수정
            if flags.get("future_date"):
                user_question = state["user_question"]
                state["user_question"] = f"{user_question}..아니다, 오늘 날짜 기준으로 해줘"

            logger.info(f"Executing final SQL query (length: {len(query)})")
            result = execute(query)
            state.update({"sql_query": query})

            # If no results found and it's a trsc query, try vector search for note1
            if (not result or is_null_only(result)) and selected_table == 'trsc':
                evernote_result = await ever_note(query)
                
                # Get original and similar notes from the result
                origin_note = evernote_result.get("origin_note", [])
                vector_notes = evernote_result.get("vector_notes", [])
                modified_query = evernote_result.get("query", query)

                if vector_notes:
                    logger.info(f"Found {len(vector_notes)} similar notes")
                    # Store vector notes in state
                    vector_notes_data = {
                        "origin_note": origin_note,
                        "vector_notes": vector_notes
                    }
                    state.update({"vector_notes": vector_notes_data})

                    # Update user question to mention the similar notes
                    origin_note_str = "', '".join(origin_note)
                    vector_note_str = "', '".join(vector_notes)

                    final_answer = f"요청을 처리하기 위해 '{origin_note_str}' 노트의 거래내역을 찾아 보았으나 검색된 결과가 없었습니다. 해당 기간 거래내역의 노트 중 유사한 노트('{vector_note_str}')로 검색한 결과는 다음과 같습니다."
                    state.update({"final_answer": final_answer})
                    flags["note_changed"] = True

                # Try executing the modified query if available
                if modified_query and modified_query != query:
                    result = execute(modified_query)
                    state.update({"sql_query": modified_query})
                    result = final_df_format(result, selected_table)

            state.update({"date_info": view_dates["main"]})

        except Exception as e:
            logger.error(f"Error in view table processing: {str(e)}")
            result = execute(query_ordered)
            state.update({"sql_query": query_ordered})

    # 결과가 없는 경우 처리
    if not result or is_null_only(result):
        logger.warning("No data found in query results")
        flags["no_data"] = True
        empty_result = []
        column_list = []
        state.update({"query_result": empty_result, "column_list": column_list})
        StateManager.update_state(trace_id, {
            "sql_query": state.get("sql_query"),
            "query_result": empty_result,
            "column_list": column_list,
            "date_info": state.get("date_info", (None, None))
        })

        return state

    logger.info(f"Query executed successfully, storing results")
    state.update({"query_result": result, "column_list": column_list})
    StateManager.update_state(trace_id, {
        "sql_query": state.get("sql_query"),
        "query_result": result,
        "column_list": column_list,
        "date_info": state.get("date_info", (None, None))
    })

    return state

async def safeguard(state: GraphState) -> GraphState:
    trace_id = state["trace_id"]
    user_question = state["user_question"]
    selected_table = state["selected_table"]
    unsafe_query = state["sql_query"]
    sql_error = state.get("sql_error", "")
    flags = state.get("flags")
    
    flags["safe_count"] = flags.get("safe_count", 0) + 1

    safe_query = await guard_query(trace_id, unsafe_query, user_question, selected_table, flags, sql_error)

    if safe_query == unsafe_query:
        flags["query_changed"] = False
        return state

    if safe_query != unsafe_query:
        flags["query_changed"] = True
        state.update({"sql_query": safe_query})

        StateManager.update_state(trace_id, {
            "sql_query": safe_query,
            "sql_error": sql_error
        })
        return state

async def respondent(state: GraphState) -> GraphState:
    """쿼리 결과를 바탕으로 최종 응답을 생성"""
    trace_id = state["trace_id"]
    user_question = state["user_question"]
    result = state["query_result"]
    selected_table = state["selected_table"]
    raw_column_list = state["column_list"]

    cleaned_result = delete_useless_col(result, raw_column_list)
    # 테이블 데이터에서는 입출금과 통화 변환이 필요 없음음

    if selected_table == "api":
        date_info = state["date_info"]
    else:
        date_info = ()
    fstring_answer = await response(trace_id, user_question, date_info, cleaned_result)

    # debuging
    state.update({"yogeumjae": fstring_answer})
    final_answer = fstring_answer
    # node.py의 respondent 함수에 추가
    logger.info(f"Final answer: {final_answer}")

    final_result = final_df_format(cleaned_result, selected_table)
    if selected_table == "api":
        final_result = is_krw(final_result)

    state.update({"final_answer": final_answer, "query_result": final_result})
    StateManager.update_state(trace_id, {
        "final_answer": final_answer,
        "query_result": final_result
    })
    return state

# async def respondent(state: GraphState) -> GraphState:
#     """쿼리 결과를 바탕으로 최종 응답을 생성"""
#     trace_id = state["trace_id"]
#     user_question = state["user_question"]
#     result = state["query_result"]
#     selected_table = state["selected_table"]
#     raw_column_list = state["column_list"]

#     cleaned_result, cleaned_column_list = delete_useless_col(result, raw_column_list)
#     # 컬럼과 데이터에서 입출금과 통화 구분
#     result_for_col, column_list = transform_data(cleaned_result, cleaned_column_list)

#     if selected_table == "api":
#         date_info = state["date_info"]
#     else:
#         date_info = ()
#     fstring_answer = await response(trace_id, user_question, selected_table, column_list, date_info)

#     # debuging
#     state.update({"yogeumjae": fstring_answer})

#     logger.info("Computing final answer using fstring template")
#     final_answer = compute_fstring(fstring_answer, result_for_col, column_list)

#     final_result = final_df_format(cleaned_result, selected_table)
#     if selected_table == "api":
#         final_result = is_krw(final_result)

#     state.update({"final_answer": final_answer, "column_list": column_list, "query_result": final_result})
#     StateManager.update_state(trace_id, {
#         "final_answer": final_answer,
#         "column_list": column_list,
#         "query_result": final_result
#     })
#     return state

async def nodata(state: GraphState) -> GraphState:
    """데이터가 없음을 설명하는 노드"""
    trace_id = state["trace_id"]
    user_question = state["user_question"]
    flags = state.get("flags")
    
    if flags.get("note_changed"):
        logger.info("Note changed flag detected, updating question context")
        vector_notes = state.get("vector_notes", {})
        vector_note_str = "', '".join(vector_notes.get("vector_notes", []))
        user_question = user_question + f" 유사한 노트('{vector_note_str}')를 활용해서도 검색해줘"

    final_answer = await no_data(trace_id, user_question)

    if flags.get("future_date"):
        final_answer = "요청주신 시점은 제가 조회가 불가능한 시점이기에 오늘 날짜를 기준으로 조회했습니다. " + final_answer

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