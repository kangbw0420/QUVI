import uuid
import traceback

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from data_class.request import RequestData
from typing import Optional

from graph.graph import make_graph


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
        # result - table()
        try:
            table = list(raw_data[0].keys())
        except IndexError as E:
            table = []
        # result {answer, table}
        result = {"question" :question,"answer": answer, "table":table}
        # SQL
        sql_query = data["sql_query"]
        
        return Output(
            status = 200,
            success = True,
            retCd = 200,
            message="질답성공",
            body = {"result": result, "raw_data": raw_data, "SQL": sql_query}
        )
        
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing input: {str(e)}")

import json
from ML.classification import classifier
from ML.regression import regressor

@api.post("/classification")
async def process_classification(request: RequestData):
    """사용자 질문에 대해 분류 분석 결과를 반환하는 엔드포인트"""
    try:
        result = await classifier.analyze_question(request.user_question)
        
        combined_result = {
            "answer": "class" + result["answer"],
            "raw_data": [result["raw_data"]]
        }
        
        final_result = {
            "status": "success",  # 나중에 제거
            "result": {
                "answer": json.dumps(combined_result, ensure_ascii=False),
                "table": []
            },
            "raw_data": [],  # 나중에 수정
            "trace_id": "100000"  # 나중에 수정
        }
        
        return final_result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in classification process: {str(e)}"
        )

@api.post("/regression")
async def process_regression(request: RequestData):
    """사용자 질문에 대해 회귀 분석 결과를 반환하는 엔드포인트"""
    try:
        result = await regressor.analyze_question(request.user_question)
        print(result.keys())
        print(result['data'])
        col = list(result['data'][0].keys())
        print(col)
        final_result = {
           "status": "success",  # 나중에 제거
           "result": {"answer": result['answer'], "table":col},  # 나중에 수정
           "raw_data": result['data'],
           "trace_id": '100000',  # 나중에 수정
        }
        return final_result
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=500,
            detail=f"Error in regression process: {str(e)}"
        )