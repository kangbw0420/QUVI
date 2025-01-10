import uuid
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from utils.config import Config

class QnAManager:
    @staticmethod
    def create_question(trace_id: str, question: str, model: str) -> str:
        """
        LLM에 질문을 보내는 시점에 QnA 레코드 생성
        Returns:
            str: 생성된 qna_id
        """
        try:
            qna_id = str(uuid.uuid4())
            
            password = quote_plus(str(Config.DB_PASSWORD))
            db_url = f"postgresql://{Config.DB_USER}:{password}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_DATABASE}"
            engine = create_engine(db_url)

            with engine.begin() as connection:
                command = text("""
                    INSERT INTO qna (
                        id,
                        trace_id,
                        question,
                        model
                    ) VALUES (
                        :qna_id,
                        :trace_id,
                        :question,
                        :model
                    )
                """)
                
                connection.execute(command, {
                    'qna_id': qna_id,
                    'trace_id': trace_id,
                    'question': question,
                    'model': model
                })

            return qna_id

        except Exception as e:
            print(f"Error in create_question: {str(e)}")
            raise

    @staticmethod
    def record_answer(qna_id: str, answer: str) -> bool:
        """
        LLM 응답을 받은 시점에 답변 기록
        Returns:
            bool: 성공 여부
        """
        try:
            password = quote_plus(str(Config.DB_PASSWORD))
            db_url = f"postgresql://{Config.DB_USER}:{password}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_DATABASE}"
            engine = create_engine(db_url)

            with engine.begin() as connection:
                command = text("""
                    UPDATE qna 
                    SET 
                        answer = :answer,
                        answer_timestamp = CURRENT_TIMESTAMP
                    WHERE id = :qna_id
                """)
                
                connection.execute(command, {
                    'qna_id': qna_id,
                    'answer': answer
                })

            return True

        except Exception as e:
            print(f"Error in record_answer: {str(e)}")
            raise