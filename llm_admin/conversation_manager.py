import uuid
from urllib.parse import quote_plus
from utils.config import Config

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

from database.postgresql import query_execute
from utils.logger import setup_logger

logger = setup_logger('conversation_manager')

load_dotenv()

def check_conversation_id(user_id: str, conversation_id: str) -> bool :
    # conversation_id 검증
    command = f"SELECT 1 FROM conversation WHERE conversation_id = '{conversation_id}';"
    # conversation_status를 체크, active면 True, 그외(completed, error)면 False
    command2 = f"SELECT conversation_status FROM conversation  WHERE conversation_id = '{conversation_id}';"

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

def make_conversation_id(user_id: str) -> str:
    conversation_id = str(uuid.uuid4())
    
    query = """
        INSERT INTO conversation (user_id, conversation_id, conversation_status)
        VALUES (%(user_id)s, %(conversation_id)s, 'active')
    """
    params = {
        'user_id': user_id,
        'conversation_id': conversation_id
    }
    
    query_execute(query, params, use_prompt_db=True)
    return conversation_id

def save_record(conversation_id: str, user_question: str, answer: str, sql_query: str) -> bool:        
    query = """
        INSERT INTO record (conversation_id, last_question, last_answer, last_sql_query)
        VALUES (%(conversation_id)s, %(question)s, %(answer)s, %(query)s)
    """
    params = {
        "conversation_id": conversation_id,
        "question": user_question,
        "answer": answer,
        "query": sql_query
    }
    
    return query_execute(query, params, use_prompt_db=True)

def extract_last_data(conversation_id:str) -> list:
    # 최대 3개의 row
    query = """
        SELECT last_question, last_answer, last_sql_query 
        FROM record 
        WHERE conversation_id = %(conversation_id)s 
        ORDER BY record_time DESC 
        LIMIT 3
    """
    
    return query_execute(query, {'conversation_id': conversation_id}, use_prompt_db=True)
