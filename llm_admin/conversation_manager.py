import uuid

from core.postgresql import query_execute
from utils.logger import setup_logger

logger = setup_logger('conversation_manager')


def check_conversation_id(conversation_id: str) -> bool:
    """conversation_id가 존재하고 status가 active인지 확인 
    Returns:
        conversation이 존재하고 active면 True, 그 외는 False
    """
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
    """새로운 conversation 생성. UUID로 ID 생성하고 status는 active로 설정"""
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