import uuid
from urllib.parse import quote_plus
from utils.config import Config

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

from database.postgresql import query_execute


load_dotenv()

def check_session_id(user_id: str, session_id: str) -> bool :
    # session_id가 개발용인지 검증
    if session_id =="DEV_SESSION_ID":
        return 0
    # 일단 session_id만 검증
    command = f"SELECT 1 FROM session WHERE session_id = '{session_id}';"
    # session_status를 체크, active면 True, 그외(completed, error)면 False
    command2 = f"SELECT session_status FROM session  WHERE session_id = '{session_id}';"

    from urllib.parse import quote_plus
    password = quote_plus(str(Config.DB_PASSWORD_PROMPT))
    db_url = f"postgresql://{Config.DB_USER_PROMPT}:{password}@{Config.DB_HOST_PROMPT}:{Config.DB_PORT_PROMPT}/{Config.DB_DATABASE_PROMPT}"
    engine = create_engine(db_url)

    with engine.begin() as connection:
        # 사용하려는 스키마 지정
        connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))

        cursor = connection.execute(text(command))
        if cursor is not None:
            cursor = connection.execute(text(command2))
            for row in cursor.fetchall():
                if row[0] == "active":
                    return 1
                else:
                    return 0
    return 0

def make_session_id(user_id: str) -> str:
    session_id = str(uuid.uuid4())
    
    query = """
        INSERT INTO session (user_id, session_id, session_status)
        VALUES (%(user_id)s, %(session_id)s, 'active')
    """
    params = {
        'user_id': user_id,
        'session_id': session_id
    }
    
    query_execute(query, params, use_prompt_db=True)
    return session_id

def save_record(session_id: str, user_question: str, answer: str, sql_query: str) -> bool:
    if session_id == "DEV_SESSION_ID":
        return False
        
    query = """
        INSERT INTO record (session_id, last_question, last_answer, last_sql_query)
        VALUES (%(session_id)s, %(question)s, %(answer)s, %(query)s)
    """
    params = {
        "session_id": session_id,
        "question": user_question,
        "answer": answer,
        "query": sql_query
    }
    
    return query_execute(query, params, use_prompt_db=True)

def extract_last_data(session_id:str) -> list:
    # 최대 3개의 row
    query = """
        SELECT last_question, last_answer, last_sql_query 
        FROM record 
        WHERE session_id = %(session_id)s 
        ORDER BY record_time DESC 
        LIMIT 3
    """
    
    return query_execute(query, {'session_id': session_id}, use_prompt_db=True)
