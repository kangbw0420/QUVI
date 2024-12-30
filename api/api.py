import sys
import uuid
import traceback

import pandas as pd
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from data_class.request import RequestData
from langfuse.decorators import langfuse_context, observe

from graph.graph import make_graph
from fuse.langfuse_handler import langfuse_handler
from fuse.langfuse_client import LangfuseClient
from utils.json_serializer import convert_dataframe_for_json

# 디버깅용 import
from datetime import datetime


class Input(BaseModel):
    task: str
    user_id: str = "default_user"  # 사용자 식별을 위한 기본값


class Feedback(BaseModel):
    trace_id: str
    score: float
    comment: str = None


api = APIRouter(tags=["api"])
graph = make_graph()

langfuse_client = LangfuseClient(base_url="http://localhost:8001")


@api.post("/execute")
async def execute(request: RequestData):
    task = request.task
    print(task)
    result = []

    if task:
        try:
            data = graph.invoke({"task": task})
            for step in data["steps"]:
                step_name = step[1]
                trans_step_name = step_name.replace("#E", "단계")
                step_desc = step[0].strip("\n")
                print(f"{trans_step_name}: {step_desc}")
                if step_name in data["dataframes"].keys():
                    result.append(data["dataframes"][step_name])

            return {"result": result}

        except Exception as e:
            print(f"Error: {str(e)}")


@api.post("/process")
async def process_input(request: RequestData):
    """프로덕션용 엔드포인트"""
    try:
        # LangGraph 실행
        data = await graph.ainvoke({"task": request.task})

        # solver에서 이미 원하는 형태로 result를 생성했으므로 그대로 반환
        return {"result": data["result"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing input: {str(e)}")


@api.post("/debug/process")
@observe()
async def debug_process_input(input: Input):
    print("\n=== Debug Process Started ===")
    trace_id = str(uuid.uuid4())

    # 실행 타임라인 초기화
    execution_timeline = {
        "planner": {"start": None, "end": None},
        "tools": [],
        "solver": {"start": None, "end": None},
    }

    def update_timeline(message: str):
        timestamp = datetime.now().isoformat()
        if "Planner -" in message:
            execution_timeline["planner"]["start"] = timestamp
        elif "Planner (Updated)" in message:
            execution_timeline["planner"]["end"] = timestamp
        elif "Tool Execution -" in message:
            execution_timeline["tools"].append({"start": timestamp, "end": None})
        elif "Tool Execution (Updated)" in message:
            if (
                execution_timeline["tools"]
                and execution_timeline["tools"][-1]["end"] is None
            ):
                execution_timeline["tools"][-1]["end"] = timestamp
        elif "Solver -" in message:
            execution_timeline["solver"]["start"] = timestamp
        elif "Solver (Updated)" in message:
            execution_timeline["solver"]["end"] = timestamp

    class PrintWrapper:
        def write(self, message):
            if "===" in message:
                update_timeline(message)
            sys.__stdout__.write(message)

    try:
        # 1. Create session
        session_response = await langfuse_client.create_session(input.user_id)
        session_id = session_response["session_id"]
        print(f"Session created: {session_id}")

        # 2. Create initial QNA entry
        qna_response = await langfuse_client.create_qna(
            user_id=input.user_id, session_id=session_id, question=input.task
        )
        qna_id = qna_response["qna_id"]
        print(f"Initial QNA created: {qna_id}")

        # 3. Process with graph
        print("Processing with graph...")
        original_stdout = sys.stdout
        sys.stdout = PrintWrapper()
        try:
            data = await graph.ainvoke(
                {"task": input.task},
                config={"callbacks": [langfuse_handler] if langfuse_handler else None},
            )
        finally:
            sys.stdout = original_stdout
        print("Graph processing completed")

        # 4. Update QNA with answer
        await langfuse_client.update_qna(
            qna_id=qna_id,
            answer=data["result"]["answer"],
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
                    "plan_string": data.get("plan_string"),
                    "steps": data.get("steps"),
                    "results": data.get("results"),
                    "result": data.get("result"),
                    "dataframes": {
                        k: {"shape": v.shape, "columns": list(v.columns)}
                        for k, v in data.get("dataframes", {}).items()
                    },
                    "calc_data": data.get("calc_data"),
                },
            }
            await langfuse_client.create_trace(trace_data)
            print(f"Trace created: {trace_id}")

        # 6. Update session status
        await langfuse_client.update_session(session_id, "completed")
        print("Session status updated to completed")

        # 7. Prepare raw_data
        raw_data = pd.DataFrame()
        if "dataframes" in data:
            dataframes = data["dataframes"]
            if dataframes:
                df_keys = sorted(dataframes.keys())
                if len(df_keys) >= 1:
                    last_key = df_keys[-1]
                    last_df = dataframes[last_key]

                    solver_table_cols = (
                        data["result"]["table"]
                        if isinstance(data["result"]["table"], list)
                        else []
                    )
                    last_df_cols = (
                        list(last_df.columns)
                        if last_df is not None and hasattr(last_df, "columns")
                        else []
                    )

                    if len(solver_table_cols) < len(last_df_cols):
                        raw_data = last_df
                    elif len(df_keys) >= 2:
                        prev_key = df_keys[-2]
                        raw_data = dataframes[prev_key]

        return {
            "status": "success",
            "result": data["result"],
            "raw_data": convert_dataframe_for_json(raw_data),
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
