import uuid

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from data_class.request import Input, Output

from graph.graph import make_graph
from utils.langfuse_handler import langfuse_handler

api = APIRouter(tags=["api"])
graph = make_graph()


@api.post("/process")
async def process_input(request: Input) -> Output:
    """프로덕션용 엔드포인트"""
    try:
        final_state = await graph.ainvoke(
            {"user_question": request.user_question,
             "last_question": request.last_question,
             "last_answer": request.last_answer,
             "last_sql_query": request.last_sql_query,
            },
            config={"callbacks": [langfuse_handler]},
        )

        # 본문 {"result": {"answer": string, "table": []}, "raw_data": [], "SQL": ""}
        answer = final_state["final_answer"]
        raw_data = final_state["query_result"]

        analyzed_question = final_state["analyzed_question"]
        sql_query = final_state["sql_query"]

        return Output(
            status=200,
            success=True,
            retCd=200,
            message="질답 성공",
            body={
                "answer": answer,
                "raw_data": raw_data,
                "analyzed_question": analyzed_question,
                "sql_query": sql_query
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing input: {str(e)}")