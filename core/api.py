import traceback

from fastapi import APIRouter
from core.dto import Input, Output
from graph.graph import make_graph
from llm_admin.conversation_manager import check_conversation_id, make_conversation_id, save_record, extract_last_data # 야돈 휴식 중 
from llm_admin.chain_manager import ChainManager
from utils.logger import setup_logger
from utils.retriever import retriever, api_recommend
from utils.error_handler import ErrorHandler

logger = setup_logger('api')

api = APIRouter(tags=["api"])
graph = make_graph()

@api.post("/process")
async def process_input(request: Input) -> Output:
    """프로덕션용 엔드포인트"""
    chain_id = None

    try:
        # 노드들의 벡터 DB 검색과 경합을 피하기 위해 초반에 추천질의 벡터 검색
        recommend_list = await retriever.get_recommend(query_text=request.user_question, top_k=4)
        # 세션 확인/생성을 가장 먼저 수행
        conversation_id = (
            request.session_id if check_conversation_id(request.session_id)
            else make_conversation_id(request.user_id)
        )
        logger.info(f"Using conversation_id: {conversation_id}")

        user_info = (request.user_id, request.use_intt_id)

        # 체인 생성
        chain_id = ChainManager.create_chain(conversation_id, request.user_question)
        logger.info(f"Created chain_id: {chain_id}")

        initial_state = {
            "chain_id": chain_id,
            "user_info": user_info,
            "fstring" : "",
            "company_id": request.company_id,
            "user_question": request.user_question,
            "flags": {
                "is_joy": False,
                "no_data": False,
                "note_changed": False,
                "future_date": False,
                "invalid_date": False,
                "query_error": False,
                "query_changed": False,
            },
            # "last_data": last_data if last_data else []
        }

        # 그래프 실행
        final_state = await graph.ainvoke(
            initial_state
        )

        # 결과 추출
        answer = final_state["final_answer"]
        raw_data = final_state["query_result"]
        sql_query = final_state["sql_query"]
        selected_table = final_state["selected_table"]

        if "date_info" not in final_state or not final_state["date_info"]:
            date_info = (None, None)
        else:
            date_info = final_state["date_info"]
        
        # recommend_list 갱신
        if selected_table == "api":
            recommend_list = api_recommend(final_state["selected_api"])

        # debugging
        fstring_n_pipe = final_state["yogeumjae"]
        kabigon = f"{sql_query}\n\n\n{fstring_n_pipe}"
        
        # save_record(conversation_id, user_question, answer, sql_query)

        ChainManager.complete_chain(chain_id, answer)

        return Output(
            status=200,
            success=True,
            retCd=200,
            message="질답 성공",
            body={
                "answer": answer,
                "raw_data": raw_data,
                "session_id": conversation_id,
                "chain_id": chain_id,
                "recommend": recommend_list,
                "is_api": selected_table == "api",
                "date_info": date_info,
                "sql_query": kabigon, # (SQL 잘 뜨는지 확인용, debug)
                "selected_table": selected_table
            }
        )

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        logger.error(traceback.format_exc())

        # 체인 오류 상태 기록
        if chain_id:
            try:
                ChainManager.mark_chain_error(chain_id, str(e))
                logger.info(f"Marked chain {chain_id} as error")
            except Exception as chain_error:
                logger.error(f"Error marking chain error: {str(chain_error)}")

        error_response = ErrorHandler.format_error_response(e)
        return error_response