import traceback

from fastapi import APIRouter, HTTPException
from data_class.request import Input, Output

from graph.graph import make_graph


from utils.langfuse_handler import langfuse_handler
from llm_admin.session_manager import check_session_id, make_session_id, save_record, extract_last_data

api = APIRouter(tags=["api"])
graph = make_graph()


@api.post("/process")
async def process_input(request: Input) -> Output:
    """프로덕션용 엔드포인트"""
    try:
        if check_session_id(request.user_id, request.session_id):
            last_data = extract_last_data(request.session_id)

            final_state = await graph.ainvoke(
                {"user_question": request.user_question,
                 "last_data": last_data
                },
                config={"callbacks": [langfuse_handler]},
                )
        else:
            final_state = await graph.ainvoke(
                {"user_question": request.user_question,
                },
                config={"callbacks": [langfuse_handler]},
            )   
 
        answer = final_state["final_answer"]
        raw_data = final_state["query_result"]
        session_id = request.session_id if check_session_id(request.user_id, request.session_id) else make_session_id(request.user_id, request.session_id)
        analyzed_question = final_state["analyzed_question"]
        sql_query = final_state["sql_query"]
        save_record(session_id, analyzed_question, answer, sql_query)


        return Output(
            status=200,
            success=True,
            retCd=200,
            session_id=session_id,
            message="질답 성공",
            body={
                "answer": answer,
                "raw_data": raw_data,
                "analyzed_question": analyzed_question,
                "sql_query": sql_query
            }
        )
        
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing input: {str(e)}")