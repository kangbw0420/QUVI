import time
import traceback
import json
from decimal import Decimal

from fastapi import APIRouter, WebSocket, HTTPException

from core.quvi_model import Input, Output, AnswerBody
from graph.graph import make_graph
from llm_admin.conversation_manager import (
    check_conversation_id,
    make_conversation_id
)
from llm_admin.chain_manager import ChainManager
from llm_admin.history_manager import get_recent_history
from utils.logger import setup_logger
from utils.retriever import retriever, api_recommend
from utils.error_handler import ErrorHandler

logger = setup_logger('api')

def convert_decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal_to_float(item) for item in obj]
    return obj

api = APIRouter(tags=["api"])
graph = make_graph()

@api.websocket("/process")
@api.post("/process")
async def process_input(request: Input = None, websocket: WebSocket = None):
    """
    사용자 질문을 처리하고 응답을 반환합니다.
    WebSocket과 HTTP POST 두 가지 방식으로 호출 가능합니다.
    """
    try:
        # WebSocket 연결 처리
        if websocket:
            await websocket.accept()
            while True:
                data = await websocket.receive_text()
                input_data = json.loads(data)
                input = Input(**input_data)
                await process_natural_language(input, websocket)
        else:
            # HTTP POST 처리
            return await process_natural_language(request)

    except Exception as e:
        logger.error(f"Process error: {e}")
        if websocket:
            try:
                await websocket.send_json({
                    "status": "error",
                    "message": str(e)
                })
            except Exception:
                logger.error(f"Failed to send error message: {e}")
        else:
            raise HTTPException(status_code=500, detail=str(e))
    finally:
        if websocket:
            try:
                await websocket.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")

async def process_natural_language(request: Input, websocket: WebSocket = None) -> Output:
    """프로덕션용 엔드포인트"""
    chain_id = None
    start_time = time.time()

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
            "is_api": False,
            "fstring" : "",
            "company_id": request.company_id,
            "user_question": request.user_question,
            "websocket": websocket,
            "flags": {
                "is_joy": False,
                "is_opendue": False,
                "no_data": False,
                "note_changed": False,
                "future_date": False,
                "invalid_date": False,
                "query_error": False,
                "query_changed": False,
                "has_next": False
            }
        }

        graph_start = time.time()

        # 그래프 실행
        final_state = await graph.ainvoke(
            initial_state
        )

        # 결과 추출
        answer = final_state["final_answer"]
        raw_data = final_state["query_result"]
        sql_query = final_state["sql_query"]
        is_api = final_state["is_api"]
        flags = final_state["flags"]
        selected_table = final_state["selected_table"]

        if "date_info" not in final_state or not final_state["date_info"]:
            date_info = (None, None)
        else:
            date_info = final_state["date_info"]
        
        # recommend_list 갱신
        if is_api:
            recommend_list = api_recommend(final_state["selected_api"])
        elif final_state["user_question"] == "next_page":
            question_for_recommend = get_recent_history(chain_id, "user_question")
            recommend_list = await retriever.get_recommend(
                query_text=question_for_recommend, top_k=4
            )

        ChainManager.complete_chain(chain_id, answer)

        # 프로파일링 데이터 조회
        from utils.profiler import profiler
        request_id = profiler.get_current_request()
        profile_data = profiler.get_profile(request_id)

        # 총 요청 처리 시간 계산
        total_time = time.time() - start_time
        total_time_ms = round(total_time * 1000, 2)

        profile_result = {
                "vector_db": profile_data.get("vector_db", {"calls": 0, "total_time_ms": 0, "avg_time_ms": 0}),
                "llm": profile_data.get("llm", {"calls": 0, "total_time_ms": 0, "avg_time_ms": 0}),
                "db_normal": profile_data.get("db_normal", {"calls": 0, "total_time_ms": 0, "avg_time_ms": 0}),
                "db_prompt": profile_data.get("db_prompt", {"calls": 0, "total_time_ms": 0, "avg_time_ms": 0}),
                "total_time_ms": total_time_ms
        }

        result = Output(
            status=200,
            success=True,
            retCd=200,
            message="질답 성공",
            body=AnswerBody(
                answer=answer,
                raw_data=raw_data,
                session_id=conversation_id,
                chain_id=chain_id,
                recommend=recommend_list,
                is_api=is_api,
                date_info=date_info,
                has_next=flags["has_next"],
                sql_query=sql_query,  # (SQL 잘 뜨는지 확인용, debug)
                selected_table=selected_table,
                profile=profile_result
            )
        )

        if websocket:
            result_dict = convert_decimal_to_float(result.dict())
            await websocket.send_json(result_dict)
        
        return result

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