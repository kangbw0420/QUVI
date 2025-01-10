import uuid
from datetime import datetime
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from utils.config import Config

class ChainManager:
    @staticmethod
    def create_chain(session_id: str, user_question: str) -> str:
        """
        새로운 체인을 생성하고 초기 상태를 기록
        Returns:
            str: 생성된 chain_id
        """
        try:
            chain_id = str(uuid.uuid4())
            
            password = quote_plus(str(Config.DB_PASSWORD))
            db_url = f"postgresql://{Config.DB_USER}:{password}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_DATABASE}"
            engine = create_engine(db_url)

            with engine.begin() as connection:
                # Parameterized query for security
                command = text("""
                    INSERT INTO chain (
                        id, 
                        session_id, 
                        chain_question, 
                        chain_status
                    ) VALUES (
                        :chain_id, 
                        :session_id, 
                        :chain_question, 
                        'active'
                    )
                """)
                
                connection.execute(command, {
                    'chain_id': chain_id,
                    'session_id': session_id,
                    'chain_question': user_question
                })

            return chain_id

        except Exception as e:
            print(f"Error in create_chain: {str(e)}")
            raise

    @staticmethod
    def complete_chain(chain_id: str, final_answer: str) -> bool:
        """
        체인 완료 시 답변과 종료 시간을 기록
        Returns:
            bool: 성공 여부
        """
        try:
            password = quote_plus(str(Config.DB_PASSWORD))
            db_url = f"postgresql://{Config.DB_USER}:{password}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_DATABASE}"
            engine = create_engine(db_url)

            with engine.begin() as connection:
                command = text("""
                    UPDATE chain 
                    SET 
                        chain_answer = :answer,
                        chain_end = CURRENT_TIMESTAMP,
                        chain_status = 'completed'
                    WHERE id = :chain_id
                """)
                
                connection.execute(command, {
                    'answer': final_answer,
                    'chain_id': chain_id
                })

            return True

        except Exception as e:
            print(f"Error in complete_chain: {str(e)}")
            raise

    @staticmethod
    def mark_chain_error(chain_id: str, error_message: str) -> bool:
        """
        체인 실행 중 오류 발생 시 상태를 error로 변경
        Returns:
            bool: 성공 여부
        """
        try:
            password = quote_plus(str(Config.DB_PASSWORD))
            db_url = f"postgresql://{Config.DB_USER}:{password}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_DATABASE}"
            engine = create_engine(db_url)

            with engine.begin() as connection:
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
            print(f"Error in mark_chain_error: {str(e)}")
            raise