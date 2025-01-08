from fastapi import APIRouter, HTTPException
from data_class.request import Input, Output

from graph.graph import make_graph
from utils.langfuse_handler import langfuse_handler
from admin.session_manager import SessionManager

api = APIRouter(tags=["api"])
graph = make_graph()


@api.post("/process")
async def process_input(request: Input) -> Output:
    """프로덕션용 엔드포인트"""
    try:
        # 세션 매니저한테 과거 질의가 있는지 물어봐서 세션값 확정짓기
        session_manager = SessionManager()
        session_id = await session_manager.get_or_create_session(
            user_id=request.user_id,
            session_id=request.session_id
        )

        # 과거 데이터 가져오기, 없으면 빈 값 가져옴.
        last_data = await session_manager.get_last_data(session_id)

        # 질문에 과거 데이터 포함해서 그래프 줌
        final_state = await graph.ainvoke(
            {
                "user_question": request.user_question,
                "last_question": last_data.analyzed_question,
                "last_answer": last_data.answer,
                "last_sql_query": last_data.sql_query
            },
            config={"callbacks": [langfuse_handler]},
        )

        # 그래프가 넣어준 값 빼내기
        answer = final_state["final_answer"]
        raw_data = final_state["query_result"]

        analyzed_question = final_state["analyzed_question"]
        sql_query = final_state["sql_query"]

        # 끝났으니 저장하라고 세션 매니저의 기록 저장 함수를 얘가 호출
        await session_manager.save_interaction(
            session_id=session_id,
            analyzed_question=analyzed_question,
            answer=answer,
            sql_query=sql_query
        )

        return Output(
            status=200,
            success=True,
            retCd=200,
            message="질답 성공",
            body={
                "session_id": session_id,
                "answer": answer,
                "raw_data": raw_data
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing input: {str(e)}")