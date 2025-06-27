from graph.types import GraphState
from graph.trace_state import trace_state
from graph.task.classifier import classify_joy, classify_api, classify_yqmd, classify_opendue
from graph.task.nl2sql import create_sql
from graph.task.respondent import response, paginated_response
from graph.task.funk import func_select
from graph.task.nodata import no_data
from graph.task.params import parameters
from graph.task.killjoy import kill_joy
from graph.task.safeguard import guard_query
from graph.task.dater import date_selector
from graph.task.commander import command

from utils.common.date_utils import get_today_str
from utils.fstring.fstring_assistant import pipe_table
from utils.logger import setup_logger
from utils.common.correct_date import check_date, correct_date_range
from utils.query.pagination import count_rows, add_limit, pagination
from utils.column.check_df import delete_useless_col
from utils.fstring.compute_fstring import compute_fstring
from utils.websocket_utils import send_ws_message
from llm_admin.history_manager import get_history, get_recent_history
from core.postgresql import query_execute


logger = setup_logger("node")


@trace_state("user_question", "sql_query")
async def next_page(state: GraphState) -> GraphState:
    # 사용자 질문을 기반으로 처리할 수 있는 노드
    user_question = state["user_question"]
    chain_id = state["chain_id"]
    if user_question == "next_page":
        recent_query = get_recent_history(chain_id, "sql_query")
        next_page_query = pagination(recent_query)

        limit = 10000
        rows = count_rows(next_page_query, limit)
        state["total_rows"] = rows
        if rows > limit:
            flags = state.get("flags")
            flags["has_next"] = True

        query_result = query_execute(next_page_query, use_prompt_db=False)
        query_result = delete_useless_col(query_result)

        state.update(
            {
                "sql_query": next_page_query,
                "query_result": query_result,
                "final_answer": "next_page",
                "date_info": get_recent_history(chain_id, "date_info"),
                "selected_table": get_recent_history(chain_id, "selected_table"),
            }
        )
    return state


@trace_state("user_question")
async def checkpoint(state: GraphState) -> GraphState:
    # 금융 관련 질의 fin과 쓸데없는 질의 joy의 임베딩 모델 활용 이진분류
    user_question = state["user_question"]
    flags = state.get("flags")

    is_joy = await classify_joy(user_question)
    if is_joy["checkpoint"] == "joy":
        flags["is_joy"] = True

    return state


@trace_state("user_question")
async def isapi(state: GraphState) -> GraphState:
    # 사용자 질문을 api로 처리할 수 있을지 판단
    user_question = state["user_question"]
    is_api = await classify_api(user_question)
    state.update({"is_api": is_api})
    return state

@trace_state("selected_table")
async def commander(state: GraphState, trace_id=None) -> GraphState:
    # 사용자 질문에 검색해야 할 table을 선택
    user_question = state["user_question"]
    chain_id = state["chain_id"]

    commander_history = get_history(chain_id, ["user_question", "selected_table"], "commander")

    selected_table = await command(trace_id, user_question, commander_history)

    state.update({"selected_table": selected_table})
    return state

@trace_state("selected_api")
async def funk(state: GraphState, trace_id=None) -> GraphState:
    # api 함수를 선택
    user_question = state["user_question"]
    chain_id = state["chain_id"]

    funk_history = get_history(chain_id, ["user_question", "selected_api"], "funk")

    selected_api = await func_select(trace_id, user_question, funk_history)

    state.update({"selected_api": selected_api})
    return state


@trace_state("sql_query", "date_info")
async def params(state: GraphState, trace_id=None) -> GraphState:
    # api 함수의 파라미터(뷰 파라미터)를 채워넣음
    selected_api = state["selected_api"]
    user_question = state["user_question"]
    company_id = state["company_id"]
    user_info = state["user_info"]
    flags = state.get("flags")
    chain_id = state["chain_id"]

    params_history = get_history(chain_id, ["user_question", "date_info"], "params")

    sql_query, date_info = await parameters(
        trace_id,
        selected_api,
        user_question,
        company_id,
        user_info,
        flags,
        params_history,
    )

    date_info = correct_date_range(date_info)

    invalid_date_message = check_date(date_info, flags)
    if invalid_date_message:
        state.update({"final_answer": invalid_date_message, "query_result": []})

    state.update({"sql_query": sql_query, "date_info": date_info})
    return state


async def yqmd(state: GraphState) -> GraphState:
    # 자금 흐름 api에서 연간/분기간/월간/일간 파라미터 결정
    user_question = state["user_question"]
    sql_query = state["sql_query"]

    query_yqmd = await classify_yqmd(user_question, sql_query)
    state.update({"sql_query": query_yqmd})

    return state

@trace_state("date_info")
async def opendue(state: GraphState) -> GraphState:
    user_question = state["user_question"]
    flags = state.get("flags")
    is_opendue = await classify_opendue(user_question)
    if is_opendue == "1":
        flags["is_opendue"] = False
        # flags["is_opendue"] = True
        # date_info = (get_today_str(), get_today_str())
        # state.update({"date_info": date_info})
    else:
        flags["is_opendue"] = False
    return state

@trace_state("date_info")
async def dater(state: GraphState, trace_id=None) -> GraphState:
    user_question = state["user_question"]
    chain_id = state["chain_id"]
    selected_table = state["selected_table"]
    flags = state.get("flags")
    date_history = get_history(chain_id, ["user_question", "date_info"], "dater")
    
    date_info = await date_selector(trace_id, user_question, selected_table, flags, date_history)
    state.update({"date_info": date_info})
    return state

@trace_state("company_id", "sql_query")
async def nl2sql(state: GraphState, trace_id=None) -> GraphState:
    # 사용자 질문을 기반으로 SQL 쿼리를 생성
    user_question = state["user_question"]
    company_id = state["company_id"]
    selected_table = state["selected_table"]
    chain_id = state["chain_id"]
    date_info = state.get("date_info", (get_today_str(), get_today_str()))

    nl2sql_history = get_history(chain_id, ["user_question", "sql_query"], "nl2sql")

    sql_query = await create_sql(
        trace_id, company_id, user_question, selected_table, date_info, nl2sql_history
    )
    await send_ws_message(state["websocket"], "nl2sql", sql_query=sql_query)

    state.update({"sql_query": sql_query})
    return state


@trace_state("sql_query", "sql_error")
async def safeguard(state: GraphState, trace_id=None) -> GraphState:
    user_question = state["user_question"]
    unsafe_query = state["sql_query"]
    selected_table = state["selected_table"]
    sql_error = state.get("sql_error", "")
    flags = state.get("flags")

    flags["safe_count"] = flags.get("safe_count", 0) + 1

    sql_query = await guard_query(
        trace_id, unsafe_query, user_question, selected_table, flags, sql_error
    )
    await send_ws_message(state["websocket"], "safeguard_end", sql_query=sql_query)

    limit = 10000
    rows = count_rows(sql_query, limit)
    state["total_rows"] = rows
    if rows > limit:
        flags["has_next"] = True
        sql_query = add_limit(sql_query)

    if sql_query == unsafe_query:
        flags["query_changed"] = False
        return state

    if sql_query != unsafe_query:
        flags["query_changed"] = True
        state.update({"sql_query": sql_query})
        return state


@trace_state("fstring_answer", "final_answer", "table_pipe", "query_result")
async def respondent(state: GraphState, trace_id=None) -> GraphState:
    # 쿼리 결과를 바탕으로 최종 응답을 생성"""
    user_question = state["user_question"]
    query_result = state["query_result"]
    is_api = state["is_api"]
    chain_id = state["chain_id"]
    has_next = state.get("flags", {}).get("has_next", False)
    total_rows = state.get("total_rows", 0)

    respondent_history = get_history(
        chain_id, ["user_question", "table_pipe", "fstring_answer", "final_answer"], "respondent"
    )

    query_result = delete_useless_col(query_result)

    # paginated answer의 경우 paginated_response를 사용해서 final_answer 생성
    if has_next:
        if isinstance(query_result, tuple) and len(query_result) == 2 and isinstance(query_result[0], list):
            data_for_table = query_result[0]
        else:
            data_for_table = query_result
        table_pipe = pipe_table(data_for_table)

        final_answer = await paginated_response(trace_id, user_question, total_rows, respondent_history)

        # paginated response의 경우 여기서 끝
        state.update(
            {
                "final_answer": final_answer,
                "query_result": query_result,
                "table_pipe": table_pipe,
            }
        )
        logger.info(f"Final answer (paginated): {final_answer}")
        return state

    if is_api:
        date_info = state["date_info"]
    else:
        date_info = ()
    fstring_answer, table_pipe = await response(
        trace_id, user_question, date_info, query_result, respondent_history
    )

    final_answer = compute_fstring(fstring_answer, query_result)
    # node.py의 respondent 함수에 추가
    logger.info(f"Final answer: {final_answer}")

    state.update(
        {
            "fstring_answer": fstring_answer,
            "table_pipe": table_pipe,
            "final_answer": final_answer,
            "query_result": query_result,
        }
    )

    return state


@trace_state("final_answer")
async def nodata(state: GraphState, trace_id=None) -> GraphState:
    # 데이터가 없음을 설명하는 노드"""
    user_question = state["user_question"]
    flags = state.get("flags")
    chain_id = state["chain_id"]

    await send_ws_message(state["websocket"], "nodata_start")

    nodata_history = get_history(chain_id, ["user_question", "final_answer"], "nodata")

    if flags.get("note_changed"):
        logger.info("Note changed flag detected, updating question context")
        vector_notes = state.get("vector_notes", {})
        vector_note_str = "', '".join(vector_notes.get("vector_notes", []))
        user_question = (
            user_question + f" 유사한 노트('{vector_note_str}')를 활용해서도 검색해줘"
        )

    final_answer = await no_data(trace_id, user_question, nodata_history)

    if flags.get("future_date"):
        final_answer = (
            "요청주신 시점은 제가 조회가 불가능한 시점이기에 오늘 날짜를 기준으로 조회했습니다. "
            + final_answer
        )

    state.update({"final_answer": final_answer})
    return state


@trace_state("final_answer")
async def killjoy(state: GraphState, trace_id=None) -> GraphState:
    # 장난하지 말고 재무 데이터나 물어보라는 노드"""
    user_question = state["user_question"]
    chain_id = state["chain_id"]

    await send_ws_message(state["websocket"], "killjoy_start")
    
    killjoy_history = get_history(
        chain_id, ["user_question", "final_answer"], "killjoy"
    )

    final_answer = await kill_joy(trace_id, user_question, killjoy_history)

    state.update({
        "final_answer": final_answer,
        "query_result": [],
        "sql_query": "",
        "selected_table": ""
    })
    return state