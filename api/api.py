import traceback

from fastapi import APIRouter, HTTPException
from api.dto import Input, Output

from graph.graph import make_graph
from llm_admin.conversation_manager import check_conversation_id, make_conversation_id, save_record, extract_last_data
from llm_admin.chain_manager import ChainManager
from utils.logger import setup_logger

logger = setup_logger('api')

api = APIRouter(tags=["api"])
graph = make_graph()

@api.post("/process")
async def process_input(request: Input) -> Output:
    """프로덕션용 엔드포인트"""
    logger.info(type(request.company_id))
    logger.info(request.company_id)
    chain_id = None
    if isinstance(request.company_id, str):
        request.company_id = {
            "main_com": [request.company_id],
            "sub_com": ['쿠콘', '비즈플레이', '웹케시벡터', '웹케시하위', '위플렉스', '웹케시글로벌']
        }
    
    logger.info(type(request.company_id))
    logger.info(request.company_id)
    
    try:
        # 세션 확인/생성을 가장 먼저 수행
        conversation_id = (
            request.session_id if check_conversation_id(request.user_id, request.session_id)
            else make_conversation_id(request.user_id)
        )
        logger.info(conversation_id)

        user_info = (request.user_id, request.use_intt_id)
        
        # last_data 조회
        last_data = extract_last_data(conversation_id) if check_conversation_id(request.user_id, conversation_id) else None
        logger.info(last_data)

        # 체인 생성
        chain_id = ChainManager.create_chain(conversation_id, request.user_question)
        logger.info(chain_id)

        initial_state = {
            "chain_id": chain_id,
            "user_info": user_info,
            "company_id": request.company_id,
            "user_question": request.user_question,
            "last_data": last_data if last_data else []
        }
        
        # 그래프 실행
        final_state = await graph.ainvoke(
            initial_state
        )
        
        # 결과 추출
        answer = final_state["final_answer"]
        raw_data = final_state["query_result"]
        user_question = final_state["user_question"]
        sql_query = final_state["sql_query"]
        
        # 기존 레코드 저장
        save_record(conversation_id, user_question, answer, sql_query)
        
        # 체인 완료 기록
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
                "sql_query": sql_query, # (SQL 잘 뜨는지 확인용, 프로덕션 제거)
            }
        )
        
    except Exception as e:
        error_detail = str(e)
        print(traceback.format_exc())
        
        # 체인 오류 상태 기록
        if chain_id:
            try:
                ChainManager.mark_chain_error(chain_id, error_detail)
            except Exception as chain_error:
                print(f"Error marking chain error: {str(chain_error)}")
        
        raise HTTPException(status_code=500, detail=f"Error processing input: {error_detail}")
