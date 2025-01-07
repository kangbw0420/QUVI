import uuid
import traceback

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from data_class.request import RequestData
from typing import Optional

from graph.graph import make_graph
from utils.langfuse_handler import langfuse_handler

# 디버깅용 import
from datetime import datetime

class Output(BaseModel):
    status: int# 200
    success: bool# True
    retCd: int # 200 
    message: str# 질답 성공
    body: dict # 본문
    
class Input(BaseModel):
    user_question: str
    user_id: str = 'default_user'
    session_id:str = 'default_session'
    last_question: Optional[str]  # 이전 그래프의 사용자 질문
    last_answer: Optional[str]    # 이전 그래프의 LLM 답변
    last_sql_query: Optional[str] # 이전 그래프의 SQL 쿼리

class Feedback(BaseModel):
    trace_id: str
    score: float
    comment: str = None


api = APIRouter(tags=["api"])
graph = make_graph()


@api.post("/process")
async def process_input(request: Input) -> Output:
    """프로덕션용 엔드포인트"""
    try:
        # 트레이스 ID 생성 (langfuse)
        # trace_id = str(uuid.uuid4())
        # print("request:", request.user_question)
        data = await graph.ainvoke(
            {"user_question": request.user_question,
             "last_question": request.last_question,
             "last_answer": request.last_answer,
             "last_sql_query": request.last_sql_query,
            }#,
            #config={"callbacks": [langfuse_handler]},
        )
        # print("data:",data)
        # 본문 {"result": {"answer": string, "table": []}, "raw_data": [], "SQL": ""}
        question = data["analyzed_question"]
        # result - answer
        answer = data["final_answer"]
        # raw_data
        raw_data = data["query_result"]
        col = list(raw_data[0].keys())
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