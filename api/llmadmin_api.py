from fastapi import APIRouter, HTTPException
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from utils.config import Config
from typing import List, Dict, Any

llmadmin_api = APIRouter(tags=["llmadmin"])

def get_db_connection():
    """Database connection helper"""
    password = quote_plus(str(Config.DB_PASSWORD_PROMPT))
    db_url = f"postgresql://{Config.DB_USER_PROMPT}:{password}@{Config.DB_HOST_PROMPT}:{Config.DB_PORT_PROMPT}/{Config.DB_DATABASE_PROMPT}"
    engine = create_engine(db_url)
    return engine

@llmadmin_api.get("/users", response_model=List[str])
async def get_users():
    """Get list of user IDs ordered by latest session"""
    try:
        engine = get_db_connection()
        with engine.begin() as connection:
            connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))
            query = """
                SELECT DISTINCT user_id 
                FROM session 
                ORDER BY user_id DESC
            """
            result = connection.execute(text(query))
            return [row[0] for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@llmadmin_api.get("/sessions/{user_id}", response_model=List[Dict[str, Any]])
async def get_sessions(user_id: str):
    """Get all sessions for a specific user"""
    try:
        engine = get_db_connection()
        with engine.begin() as connection:
            connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))
            query = """
                SELECT session_start, session_end, session_status, session_id
                FROM session 
                WHERE user_id = :user_id
                ORDER BY session_start DESC
            """
            result = connection.execute(text(query), {"user_id": user_id})
            return [dict(row) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@llmadmin_api.get("/chains/{session_id}", response_model=List[Dict[str, Any]])
async def get_chains(session_id: str):
    """Get all chains for a specific session"""
    try:
        engine = get_db_connection()
        with engine.begin() as connection:
            connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))
            query = """
                SELECT chain_question, chain_start, chain_end, chain_status, id
                FROM chain 
                WHERE session_id = :session_id
                ORDER BY chain_start DESC
            """
            result = connection.execute(text(query), {"session_id": session_id})
            return [dict(row) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@llmadmin_api.get("/traces/{chain_id}", response_model=Dict[str, Any])
async def get_traces(chain_id: str):
    """Get chain details and all traces for a specific chain"""
    try:
        engine = get_db_connection()
        with engine.begin() as connection:
            connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))
            
            # Get chain details
            chain_query = """
                SELECT chain_question, chain_answer, chain_start, chain_end, chain_status
                FROM chain 
                WHERE id = :chain_id
            """
            chain_result = connection.execute(text(chain_query), {"chain_id": chain_id}).first()
            
            if not chain_result:
                raise HTTPException(status_code=404, detail="Chain not found")
            
            # Get traces
            trace_query = """
                SELECT id, node_type, trace_start, trace_end, trace_status
                FROM trace 
                WHERE chain_id = :chain_id
            """
            trace_result = connection.execute(text(trace_query), {"chain_id": chain_id})
            
            return {
                "chain": dict(chain_result),
                "traces": [dict(row) for row in trace_result]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@llmadmin_api.get("/qnas/{trace_id}", response_model=List[Dict[str, Any]])
async def get_qnas(trace_id: str):
    """Get all QnAs for a specific trace"""
    try:
        engine = get_db_connection()
        with engine.begin() as connection:
            connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))
            query = """
                SELECT question, answer, model, question_timestamp, answer_timestamp
                FROM qna 
                WHERE trace_id = :trace_id
                ORDER BY question_timestamp ASC
            """
            result = connection.execute(text(query), {"trace_id": trace_id})
            return [dict(row) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@llmadmin_api.get("/states/{trace_id}", response_model=List[Dict[str, Any]])
async def get_states(trace_id: str):
    """Get all states for a specific trace"""
    try:
        engine = get_db_connection()
        with engine.begin() as connection:
            connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))
            query = """
                SELECT id, user_question, selected_table, analyzed_question, 
                       sql_query, query_result_stats, query_result, final_answer
                FROM state 
                WHERE trace_id = :trace_id
                ORDER BY id ASC
            """
            result = connection.execute(text(query), {"trace_id": trace_id})
            return [dict(row) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))