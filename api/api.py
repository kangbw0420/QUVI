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
from utils.json_serializer import convert_dataframe_for_json

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
           config={"callbacks": [langfuse_handler]}
       )
       # solver에서 이미 원하는 형태로 result를 생성했으므로 그대로 반환
       return {
           "result": data["final_answer"],
           "trace_id": trace_id  # trace_id도 반환
       }
   except Exception as e:
       raise HTTPException(
           status_code=500, 
           detail=f"Error processing input: {str(e)}"
       )

@observe()
@api.post("/debug/process")
async def debug_process_input(input: Input):
    print("\n=== Debug Process Started ===")
    trace_id = str(uuid.uuid4())

    # 실행 타임라인 초기화
    execution_timeline = {
        "question_analyzer": {"start": None, "end": None},
        "sql_creator": {"start": None, "end": None},
        "result_executor": {"start": None, "end": None},
        "sql_respondent": {"start": None, "end": None},
    }

    try:
        # 1. Create session
        session_response = await langfuse_client.create_session(input.user_id)
        session_id = session_response["session_id"]
        print(f"Session created: {session_id}")

        # 2. Create initial QNA entry
        qna_response = await langfuse_client.create_qna(
            user_id=input.user_id, session_id=session_id, question=input.user_question
        )
        qna_id = qna_response["qna_id"]
        print(f"Initial QNA created: {qna_id}")

        # 3. Process with graph
        print("Processing with graph...")
        original_stdout = sys.stdout
        try:
            data = await graph.ainvoke(
                {"user_question": input.user_question},
                config={"callbacks": [langfuse_handler] if langfuse_handler else None},
            )
        finally:
            sys.stdout = original_stdout
        print("Graph processing completed")

        # 4. Update QNA with answer
        await langfuse_client.update_qna(
            qna_id=qna_id,
            answer=data["final_answer"],
            answer_timestamp=datetime.utcnow().isoformat(),
            trace_id=trace_id,
        )
        print(f"QNA updated with answer and trace_id")

        # 5. Create trace
        if langfuse_handler:
            trace_data = {
                "id": trace_id,
                "trace_type": "process",
                "node_type": "main",
                "model": "claude-3.5-sonnet",
                "meta_data": {
                    "analyzed_question": data.get("analyzed_question"),
                    "sql_query": data.get("sql_query"),
                    "query_result_stats": data.get("query_result_stats"),
                    "query_result": data.get("query_result"),
                    "final_answer": data.get("final_answer"),
                },
            }
            await langfuse_client.create_trace(trace_data)
            print(f"Trace created: {trace_id}")

        # 6. Update session status
        await langfuse_client.update_session(session_id, "completed")
        print("Session status updated to completed")

        return {
            "status": "success",
            "result": data["final_answer"],
            "raw_data": data["query_result"],
            "trace_id": trace_id,
            "session_id": session_id,
            "qna_id": qna_id,
            "execution_timeline": execution_timeline,
        }

    except Exception as e:
        print(f"Error in debug_process_input: {str(e)}")
        if "session_id" in locals():
            await langfuse_client.update_session(session_id, "error")
        raise HTTPException(
            status_code=500, detail={"error": str(e), "trace": traceback.format_exc()}
        )