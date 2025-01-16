from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import quote_plus
import asyncpg

from utils.config import Config
from typing import List, Dict, Any

llmadmin_api = APIRouter(tags=["llmadmin"])

async def get_db_connection():
    """비동기 Database connection helper"""
    password = quote_plus(str(Config.DB_PASSWORD_PROMPT))
    db_url = f"postgresql+asyncpg://{Config.DB_USER_PROMPT}:{password}@{Config.DB_HOST_PROMPT}:{Config.DB_PORT_PROMPT}/{Config.DB_DATABASE_PROMPT}"
    engine = create_async_engine(db_url)
    return engine

'''
(향후 구현)
/login
/groups: 유저 그룹을 누르면 유저 목록이 나온다 -- 유저와 그룹(회사/권한) 리스트를 받아야 함
/users/{group_id?}: 그룹별 유저 목록 -- 유저와 그룹(회사/권한) 매핑이 어떠한지 봐야 함
'''

@llmadmin_api.get("/users", response_model=List[str])
async def get_users():
    """user_id 리스트를 user_id의 내림차순으로 가져온다"""
    try:
        engine = await get_db_connection()
        async with engine.begin() as connection:
            await connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))
            query = """
                SELECT DISTINCT user_id 
                FROM session 
                ORDER BY user_id DESC
            """
            result = await connection.execute(text(query))
            return [row[0] for row in await result.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@llmadmin_api.get("/sessions/{user_id}", response_model=List[Dict[str, Any]])
async def get_sessions(user_id: str):
    """user_id에 해당하는 session을 모두 검색해 session_start의 최신순으로 가져온다"""
    try:
        engine = await get_db_connection()
        with engine.begin() as connection:
            await connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))
            query = """
                SELECT session_start, session_end, session_status, session_id
                FROM session 
                WHERE user_id = :user_id
                ORDER BY session_start DESC
            """
            result = await connection.execute(text(query), {"user_id": user_id})
            return [dict(row._mapping) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@llmadmin_api.get("/chains/{session_id}", response_model=List[Dict[str, Any]])
async def get_chains(session_id: str):
    """session_id에 해당하는 chain들을 모두 검색해 chain_start의 최신순으로 가져온다"""
    try:
        engine = await get_db_connection()
        async with engine.begin() as connection:
            await connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))
            query = """
                SELECT chain_question, chain_start, chain_end, chain_status, id
                FROM chain 
                WHERE session_id = :session_id
                ORDER BY chain_start DESC
            """
            result = await connection.execute(text(query), {"session_id": session_id})
            return [dict(row._mapping) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@llmadmin_api.get("/traces/{chain_id}", response_model=Dict[str, Any])
async def get_traces(chain_id: str):
    """chain_id에 해당하는 chain의 정보와 그 chain에 속한 trace 정보를 모두 가져온다"""
    try:
        engine = await get_db_connection()
        async with engine.begin() as connection:
            await connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))
            
            # Get chain details
            chain_query = """
                SELECT chain_question, chain_answer, chain_start, chain_end, chain_status
                FROM chain 
                WHERE id = :chain_id
            """
            result = await connection.execute(text(chain_query), {"chain_id": chain_id})
            chain_result = result.first()
            
            if not chain_result:
                raise HTTPException(status_code=404, detail="Chain not found")
            
            # Get traces
            trace_query = """
                SELECT id, node_type, trace_start, trace_end, trace_status
                FROM trace 
                WHERE chain_id = :chain_id
            """
            trace_result = await connection.execute(text(trace_query), {"chain_id": chain_id})
            
            return {
                "chain": dict(chain_result._mapping),
                "traces": [dict(row._mapping) for row in trace_result]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@llmadmin_api.get("/qnas/{trace_id}", response_model=List[Dict[str, Any]])
async def get_qnas(trace_id: str):
    """trace_id에 해당하는 qna들을 question_timestamp가 오래된 순으로 가져온다"""
    try:
        engine = await get_db_connection()
        async with engine.begin() as connection:
            await connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))
            query = """
                SELECT question, answer, model, question_timestamp, answer_timestamp
                FROM qna 
                WHERE trace_id = :trace_id
                ORDER BY question_timestamp ASC
            """
            result = await connection.execute(text(query), {"trace_id": trace_id})
            return [dict(row._mapping) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@llmadmin_api.get("/states/{trace_id}", response_model=List[Dict[str, Any]])
async def get_states(trace_id: str):
    """trace_id에 해당하는 state들을 id의 오름차순으로 가져온다"""
    try:
        engine = await get_db_connection()
        async with engine.begin() as connection:
            await connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))
            query = """
                SELECT id, user_question, selected_table, analyzed_question, 
                       sql_query, query_result_stats, query_result, final_answer
                FROM state 
                WHERE trace_id = :trace_id
                ORDER BY id ASC
            """
            result = await connection.execute(text(query), {"trace_id": trace_id})
            return [dict(row._mapping) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))