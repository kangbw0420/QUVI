from typing import Optional
import uuid

class LastData:
    def __init__(self, analyzed_question: str = "", answer: str = "", sql_query: str = ""):
        self.analyzed_question = analyzed_question
        self.answer = answer
        self.sql_query = sql_query

class SessionManager:
    def __init__(self, db_engine):
        self.db = db_engine

    async def get_or_create_session(self, user_id: str, session_id: Optional[str] = None) -> str:
        if not session_id:
            session_id = str(uuid.uuid4())
            # 새 세션 DB에 기록
            await self.create_session(user_id, session_id)
        return session_id

    async def get_last_data(self, session_id: str) -> LastData:
        if not session_id:
            return LastData()
            
        # DB에서 해당 session_id의 가장 최근 기록 조회
        query = """
            SELECT analyzed_question, answer, sql_query 
            FROM conversation_history 
            WHERE session_id = :session_id 
            ORDER BY created_at DESC LIMIT 1
        """
        result = await self.db.fetch_one(query, {"session_id": session_id})
        
        if not result:
            return LastData()
            
        return LastData(
            analyzed_question=result['analyzed_question'],
            answer=result['answer'],
            sql_query=result['sql_query']
        )