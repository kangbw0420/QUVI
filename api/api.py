import traceback

from fastapi import APIRouter, HTTPException
from api.dto import Input, Output

from graph.graph import make_graph
from llm_admin.conversation_manager import check_conversation_id, make_conversation_id, save_record, extract_last_data
from llm_admin.chain_manager import ChainManager
from utils.logger import setup_logger
from utils.retriever import retriever
from utils.error_handler import ErrorHandler

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
        # last_data = extract_last_data(conversation_id) if check_conversation_id(conversation_id) else None
        # logger.info(f"last_data: {last_data}")

        # 체인 생성
        chain_id = ChainManager.create_chain(conversation_id, request.user_question)
        logger.info(f"chain_id: {chain_id}")

        initial_state = {
            "chain_id": chain_id,
            "user_info": user_info,
            "access_company_list": request.access_company_list,
            "user_question": request.user_question,
            "flags": {
                "no_data": False,
                "no_access": False,
                "com_changed": False,
                "date_changed": False
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
        user_question = final_state["user_question"]
        sql_query = final_state["sql_query"]
        selected_table = final_state["selected_table"]
        referral_list = final_state.get("flags", {}).get("referral", [])

        if "date_info" not in final_state or not final_state["date_info"]:
            date_info = (None, None)
        else:
            date_info = final_state["date_info"]
        
        # recommend_list 갱신
        if referral_list:
            # referral_list의 길이 확인
            n_referral = len(referral_list)
            if n_referral >= 3:
                # referral_list가 3개 이상이면 전부 교체
                recommend_list = referral_list[:3]
            else:
                # referral_list가 1개 또는 2개면 나머지를 recommend_list로 채움
                recommend_list = referral_list + recommend_list[:(3-n_referral)]

        # for shot making
        column_list = final_state["column_list"]
        column_list_str = ", ".join(str(col) for col in column_list)
        kabigon = f"{sql_query}\n\n\n{column_list_str}"
        
        # 기존 레코드 저장
        # save_record(conversation_id, user_question, answer, sql_query)
        
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
                "chain_id": chain_id,
                "recommend": recommend_list,
                "is_api": selected_table == "api",
                "date_info": date_info,
                "sql_query": kabigon, # (SQL 잘 뜨는지 확인용, 프로덕션 제거)
            }
        )
        
    except Exception as e:
        logger.error(f"---------------Error---------------")
        logger.error(str(e))
        logger.error(traceback.format_exc())
        
        # 체인 오류 상태 기록
        if chain_id:
            try:
                ChainManager.mark_chain_error(chain_id, str(e))
            except Exception as chain_error:
                print(f"Error marking chain error: {str(chain_error)}")

        # error_detail = str(e)
        # raise HTTPException(status_code=500, detail=f"Error processing input: {error_detail}")
        
        error_response = ErrorHandler.format_error_response(e)
        return error_response
