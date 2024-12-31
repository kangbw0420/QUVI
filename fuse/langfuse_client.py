import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd
from decimal import Decimal


class JSONSerializer(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, pd.Timestamp)):
            return obj.isoformat()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict("records")
        elif isinstance(obj, pd.Series):
            return obj.to_dict()
        elif isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class LangfuseClient:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url

    async def create_session(self, user_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/session", json={"user_id": user_id}
            )

            if response.status_code != 200:
                raise Exception(f"Error creating session: {response.text}")

            return response.json()

    async def update_session(self, session_id: str, status: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/api/session/{session_id}", params={"status": status}
            )

            if response.status_code != 200:
                raise Exception(f"Error updating session: {response.text}")

            return response.json()

    async def create_qna(
        self,
        user_id: str,
        session_id: str,
        question: str,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/qna",
                json={
                    "user_id": user_id,
                    "session_id": session_id,
                    "question": question,
                    "trace_id": trace_id,
                },
            )

            if response.status_code != 200:
                raise Exception(f"Error creating QNA: {response.text}")

            return response.json()

    async def update_qna(
        self,
        qna_id: str,
        answer: Optional[str] = None,
        answer_timestamp: Optional[datetime] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/api/qna/{qna_id}",
                json={
                    "answer": answer,
                    "answer_timestamp": answer_timestamp,
                    "trace_id": trace_id,
                },
            )

            if response.status_code != 200:
                raise Exception(f"Error updating QNA: {response.text}")

            return response.json()

    async def create_trace(self, trace_data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            print(
                f"\nCreating trace with data: {json.dumps(trace_data, indent=2, cls=JSONSerializer)}"
            )

            print(json.dumps(trace_data, cls=JSONSerializer))
            response = await client.post(
                f"{self.base_url}/api/trace",
                json=json.dumps(trace_data, cls=JSONSerializer),
            )

            if response.status_code != 200:
                raise Exception(f"Error creating trace: {response.text}")

            result = response.json()
            print(f"Trace created successfully: {result}")
            return result

    async def add_feedback(
        self, trace_id: str, score: float, comment: Optional[str] = None
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/trace/{trace_id}/feedback",
                json={"score": score, "comment": comment},
            )

            if response.status_code != 200:
                raise Exception(f"Error adding feedback: {response.text}")

            return response.json()

    async def get_trace(self, trace_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/trace/{trace_id}")

            if response.status_code != 200:
                raise Exception(f"Error getting trace: {response.text}")

            return response.json()

    async def get_session_qnas(self, session_id: str) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/session/{session_id}/qnas"
            )

            if response.status_code != 200:
                raise Exception(f"Error getting session QNAs: {response.text}")

            return response.json()
