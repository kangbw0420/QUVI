import uuid

from core.postgresql import query_execute
from utils.logger import setup_logger

logger = setup_logger('trace_manager')

class TraceManager:

    def create_trace(chain_id: str, node_type: str) -> str:
        """노드 실행 시작 시 trace 기록 생성
        Returns:
            str: 생성된 trace_id
        """
        try:
            trace_id = str(uuid.uuid4())
            
            query = """
                INSERT INTO trace (
                    id,
                    chain_id,
                    node_type,
                    trace_status
                ) VALUES (
                    %(trace_id)s,
                    %(chain_id)s,
                    %(node_type)s,
                    'active'
                )
            """
            params = {
                'trace_id': trace_id,
                'chain_id': chain_id,
                'node_type': node_type
            }
            
            query_execute(query, params, use_prompt_db=True)
            return trace_id

        except Exception as e:
            logger.error(f"Error in create_trace: {str(e)}")
            raise

    def complete_trace(trace_id: str) -> bool:
        """노드 실행 완료 시 trace 상태 업데이트"""
        try:
            query = """
                UPDATE trace 
                SET 
                    trace_end = CURRENT_TIMESTAMP,
                    trace_status = 'completed'
                WHERE id = %(trace_id)s
            """
            
            return query_execute(query, {'trace_id': trace_id}, use_prompt_db=True)

        except Exception as e:
            logger.error(f"Error in complete_trace: {str(e)}")
            raise

    def mark_trace_error(trace_id: str) -> bool:
        """trace 상태를 error로 변경하고 종료 시간 기록
        Returns:
            bool: 성공 여부
        """
        try:
            query = """
                UPDATE trace 
                SET 
                    trace_end = CURRENT_TIMESTAMP,
                    trace_status = 'error'
                WHERE id = %(trace_id)s
            """
            
            return query_execute(query, {'trace_id': trace_id}, use_prompt_db=True)

        except Exception as e:
            logger.error(f"Error in mark_trace_error: {str(e)}")
            raise