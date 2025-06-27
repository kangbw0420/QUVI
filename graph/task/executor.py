from graph.types import GraphState
from graph.trace_state import trace_state
from core.postgresql import query_execute

from utils.query.pagination import count_rows, add_limit
from utils.query.ever_note import ever_note
from utils.query.view.view_table import view_table
from utils.query.filter_com import add_com_condition
from utils.query.modify_name import modify_stock, modify_bank
from utils.query.orderby import add_order_by
from utils.column.find_column import find_column_conditions
from utils.column.check_df import is_null_only
from utils.logger import setup_logger
from utils.websocket_utils import send_ws_message

logger = setup_logger("executor")

@trace_state("sql_query", "query_result", "date_info")
async def executor(state: GraphState) -> GraphState:
    # SQL 쿼리를 실행하고 결과를 분석
    flags = state.get("flags")
    date_info = state.get("date_info")
    raw_query = state.get("sql_query")
    query_result = []

    if "safe_count" not in flags:
        flags["safe_count"] = 0

    if state["is_api"]:
        
        logger.info(f"Executing API query: {raw_query}")
        try:
            query_result = query_execute(raw_query, use_prompt_db=False)
            if query_result:
                await send_ws_message(
                    state["websocket"],
                    "executor",
                    result_row=len(query_result),
                    result_column=len(query_result[0])
                )
            state.update({"sql_query": raw_query, "query_result": query_result})
            if not query_result:
                flags["no_data"] = True
        except Exception as e:
            raise

    else:
        company_id = state["company_id"]

        # 권한 있는 회사/계좌 검사
        query_right_com = add_com_condition(raw_query, company_id)

        # 주식종목/은행명 매핑 변환
        query_right_stock = modify_stock(query_right_com)
        query_right_bank = modify_bank(query_right_stock)

        # order by 추가
        query_ordered = add_order_by(query_right_bank)

        user_info = state.get("user_info")
        flags = state.get("flags")
        try:
            view_query = view_table(query_ordered, company_id, user_info, date_info, flags)

            limit = 100
            rows = count_rows(view_query, limit)
            state["total_rows"] = rows
            if rows > limit:
                flags = state.get("flags")
                flags["has_next"] = True
                view_query = add_limit(view_query)

            query_result = query_execute(view_query, use_prompt_db=False)
            if query_result:
                await send_ws_message(
                    state["websocket"],
                    "executor",
                    result_row=len(query_result),
                    result_column=len(query_result[0])
                )
            state.update({"sql_query": view_query})

            # note1 조건이 있고 결과가 없는 경우에만 vector search 시도
            try:
                note_conditions = find_column_conditions(view_query, "note1")

                if (not query_result or is_null_only(query_result)) and note_conditions:
                    evernote_result = await ever_note(view_query)

                    # Get original and similar notes from the result
                    origin_note = evernote_result.get("origin_note", [])
                    vector_notes = evernote_result.get("vector_notes", [])
                    modified_query = evernote_result.get("query", view_query)

                    if vector_notes:
                        logger.info(f"Found {len(vector_notes)} similar notes")
                        # Store vector notes in state
                        vector_notes_data = {
                            "origin_note": origin_note,
                            "vector_notes": vector_notes,
                        }
                        state.update({"vector_notes": vector_notes_data})

                        # Update user question to mention the similar notes
                        origin_note_str = "', '".join(origin_note)
                        vector_note_str = "', '".join(vector_notes)

                        final_answer = f"요청을 처리하기 위해 '{origin_note_str}' 노트의 거래내역을 찾아 보았으나 검색된 결과가 없었습니다. 해당 기간 거래내역의 노트 중 유사한 노트('{vector_note_str}')로 검색한 결과는 다음과 같습니다."
                        state.update({"final_answer": final_answer})
                        flags["note_changed"] = True

                    # Try executing the modified query if available
                    if modified_query and modified_query != view_query:
                        query_result = query_execute(
                            modified_query, use_prompt_db=False
                        )
                        state.update({"sql_query": modified_query})
            except Exception as e:
                logger.error(f"Error checking note conditions: {str(e)}")

        except Exception as e:
            logger.error(f"Error in executor: {str(e)}")

    # 결과가 없는 경우 처리
    if not query_result or is_null_only(query_result):
        logger.warning("No data found in query results")
        flags["no_data"] = True
        query_result = []
        state.update({"query_result": query_result})
        return state

    logger.info("Query executed successfully, storing results")
    state.update({"query_result": query_result})
    return state