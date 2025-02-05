import traceback

from fastapi import APIRouter, HTTPException
from api.dto import Input, Output

from graph.graph import make_graph
from llm_admin.conversation_manager import check_conversation_id, make_conversation_id, save_record, extract_last_data
from llm_admin.chain_manager import ChainManager
from utils.logger import setup_logger
from utils.retriever import retriever

logger = setup_logger('api')

api = APIRouter(tags=["api"])
graph = make_graph()

@api.post("/process")
async def process_input(request: Input) -> Output:
    """프로덕션용 엔드포인트"""
    logger.info(f"access_company_list: {request.access_company_list}")
    chain_id = None
    
    try:
        # 노드들의 벡터 DB 검색과 경합을 피하기 위해 초반에 추천질의 벡터 검색
        recommend_list = await retriever.get_recommend(
            query_text=request.user_question,
            collection_name="hall_of_fame",
            top_k=4
        )
        logger.info(recommend_list)
        
        # 세션 확인/생성을 가장 먼저 수행
        conversation_id = (
            request.session_id if check_conversation_id(request.session_id)
            else make_conversation_id(request.user_id)
        )
        logger.info(f"conversation_id: {conversation_id}")

        user_info = (request.user_id, request.use_intt_id)
        
        # last_data 조회
        last_data = extract_last_data(conversation_id) if check_conversation_id(conversation_id) else None
        logger.info(f"last_data: {last_data}")

        # 체인 생성
        chain_id = ChainManager.create_chain(conversation_id, request.user_question)
        logger.info(f"chain_id: {chain_id}")

        initial_state = {
            "chain_id": chain_id,
            "user_info": user_info,
            "access_company_list": request.access_company_list,
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

        # for shot making
        query_result_stats = final_state["query_result_stats"]
        stats_str = ''.join(query_result_stats) if isinstance(query_result_stats, list) else str(query_result_stats)
        kabigon = f"{chain_id}$$$$$$\n\n\n{sql_query}\n\n\n{stats_str}"
        

        
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
                "recommend": recommend_list,
                "sql_query": kabigon, # (SQL 잘 뜨는지 확인용, 프로덕션 제거)
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
