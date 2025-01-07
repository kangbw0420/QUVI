import uuid

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from data_class.request import RequestData

from graph.graph import make_graph
from utils.langfuse_handler import langfuse_handler

class Input(BaseModel):
    user_question: str
    user_id: str = "default_user"  # 사용자 식별을 위한 기본값


api = APIRouter(tags=["api"])
graph = make_graph()


@api.post("/process")
async def process_input(request: RequestData):
    """프로덕션용 엔드포인트"""
    try:
        # 트레이스 ID 생성
        trace_id = str(uuid.uuid4())

        data = await graph.ainvoke(
            {"user_question": request.user_question},
            config={"callbacks": [langfuse_handler]},
        )
        # result
        answer = data["final_answer"]

        # raw_data
        raw_data = data["query_result"]
        col = list(raw_data[0].keys()) if raw_data else []
        print(col)
        result = {"answer": answer, "table":col}


        return {
            "status": "success",  # 이 부분은 나중에 제거 필요
            "result": result,
            "raw_data": raw_data,
            "trace_id": trace_id,
        }  # trace_id도 반환
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing input: {str(e)}")