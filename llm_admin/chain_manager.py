import uuid
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

from utils.config import Config
from database.postgresql import query_execute
from utils.logger import setup_logger

logger = setup_logger('chain_manager')

class ChainManager:

    def create_chain(conversation_id: str, user_question: str) -> str:
        """새로운 체인을 생성하고 초기 상태를 기록
        Returns:
            str: 생성된 chain_id
        """
        try:
            chain_id = str(uuid.uuid4())
            
            query = """
                INSERT INTO chain (
                    id, 
                    conversation_id, 
                    chain_question, 
                    chain_status
                ) VALUES (
                    %(chain_id)s, 
                    %(conversation_id)s, 
                    %(chain_question)s, 
                    'active'
                )
            """
            params = {
                'chain_id': chain_id,
                'conversation_id': conversation_id,
                'chain_question': user_question
            }
            
            query_execute(query, params, use_prompt_db=True)
            return chain_id

        except Exception as e:
            logger.error(f"Error in create_chain: {str(e)}")
            raise

    def complete_chain(chain_id: str, final_answer: str) -> bool:
        """체인 완료 시 답변과 종료 시간을 기록
        Returns:
            bool: 성공 여부
        """
        try:
            query = """
                UPDATE chain 
                SET 
                    chain_answer = %(answer)s,
                    chain_end = CURRENT_TIMESTAMP,
                    chain_status = 'completed'
                WHERE id = %(chain_id)s
            """
            params = {
                'answer': final_answer,
                'chain_id': chain_id
            }
            
            return query_execute(query, params, use_prompt_db=True)

        except Exception as e:
            logger.error(f"Error in complete_chain: {str(e)}")
            raise

    def mark_chain_error(chain_id: str, error_message: str) -> bool:
        """체인 실행 중 오류 발생 시 상태를 error로 변경
        Returns:
            bool: 성공 여부
        """
        try:
            password = quote_plus(str(Config.DB_PASSWORD_PROMPT))
            db_url = f"postgresql://{Config.DB_USER_PROMPT}:{password}@{Config.DB_HOST_PROMPT}:{Config.DB_PORT_PROMPT}/{Config.DB_DATABASE_PROMPT}"
            engine = create_engine(db_url)

            with engine.begin() as connection:
                # 사용하려는 스키마 지정
                connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))

                command = text("""
                    UPDATE chain 
                    SET 
                        chain_answer = :error_message,
                        chain_end = CURRENT_TIMESTAMP,
                        chain_status = 'error'
                    WHERE id = :chain_id
                """)
                
                connection.execute(command, {
                    'error_message': error_message,
                    'chain_id': chain_id
                })

            return True

        except Exception as e:
            logger.error(f"Error in mark_chain_error: {str(e)}")
            raise