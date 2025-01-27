import uuid
from urllib.parse import quote_plus
from utils.config import Config

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

from database.postgresql import query_execute
from utils.logger import setup_logger

logger = setup_logger('conversation_manager')

load_dotenv()

def check_conversation_id(user_id: str, conversation_id: str) -> bool:
    logger.info("check_conversation_id start")
    # conversation_id 검증
    check_exists_query = """
        SELECT 1 
        FROM conversation 
        WHERE conversation_id = %(conversation_id)s
    """
    
    # conversation_status를 체크, active면 True, 그외(completed, error)면 False
    check_status_query = """
        SELECT conversation_status 
        FROM conversation 
        WHERE conversation_id = %(conversation_id)s
    """
    
    params = {'conversation_id': conversation_id}
    
    # 존재 여부 확인
    exists_result = query_execute(check_exists_query, params, use_prompt_db=True)
    if not exists_result:
        return 0
    logger.info("exists_result checked")
        
    # 상태 확인
    status_result = query_execute(check_status_query, params, use_prompt_db=True)
    if status_result and status_result[0]['conversation_status'] == 'active':
        return 1
    logger.info("status_result checked")
        
    return 0

def make_conversation_id(user_id: str) -> str:
    conversation_id = str(uuid.uuid4())
    logger.info("make_conversation_id start")
    query = """
        INSERT INTO conversation (user_id, conversation_id, conversation_status)
        VALUES (%(user_id)s, %(conversation_id)s, 'active')
    """
    params = {
        'user_id': user_id,
        'conversation_id': conversation_id
    }
    
    query_execute(query, params, use_prompt_db=True)
    logger.info("make_conversation_id end")
    return conversation_id

def save_record(conversation_id: str, user_question: str, answer: str, sql_query: str) -> bool:        
    logger.info("save_record start")
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
    logger.info("save_record end")
    
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
