import sys
import uuid
import traceback

import pandas as pd
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from data_class.request import RequestData
from langfuse.decorators import observe

from graph.graph import make_graph
from fuse.langfuse_handler import langfuse_handler
from fuse.langfuse_client import LangfuseClient

# 디버깅용 import
from datetime import datetime


class Input(BaseModel):
    user_question: str
    user_id: str = "default_user"  # 사용자 식별을 위한 기본값


class Feedback(BaseModel):
    trace_id: str
    score: float
    comment: str = None


api = APIRouter(tags=["api"])
graph = make_graph()

langfuse_client = LangfuseClient(base_url="http://localhost:8001")


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