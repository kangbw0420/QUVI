import uuid
from typing import Any
from sqlalchemy import create_engine, text
from langchain_core.prompts import ChatPromptTemplate
from urllib.parse import quote_plus
from utils.config import Config

class QnAManager:
    def format_message_str(self, msg_str: str) -> str:
        messages = []
        # 각 메시지를 분리
        parts = msg_str.strip('[]').split('), ')
        
        for part in parts:
            # Role 추출 
            if 'SystemMessage' in part:
                role = 'system'
                content_start = part.find("content='") + 9
                content_end = part.find("'", content_start)
                content = part[content_start:content_end]
            elif 'HumanMessagePromptTemplate' in part:
                role = 'user'
                content_start = part.find("template='") + 10
                content_end = part.rfind("'")
                content = part[content_start:content_end]
            elif 'AIMessagePromptTemplate' in part:
                role = 'assistant'
                content_start = part.find('template="') + 10
                content_end = part.rfind('"')
                content = part[content_start:content_end]
            else:
                continue
                
            # 내용이 있는 경우만 추가
            if content.strip():
                messages.append(f"{role}\n{content}")
        
        return "\n\n".join(messages)

    def create_question(self, trace_id: str, question: Any, model: str) -> str:
        """
        LLM에 질문을 보내는 시점에 QnA 레코드 생성
        Args:
            trace_id: 추적 ID
            question: 질문 (ChatPromptTemplate 또는 str)
            model: 모델명
        Returns:
            str: 생성된 qna_id
        """
        try:
            qna_id = str(uuid.uuid4())
            
            # ChatPromptTemplate인 경우 문자열로 변환
            if isinstance(question, ChatPromptTemplate):
                question_str = self.format_message_str(str(question.messages))
            else:
                question_str = str(question)
            
            password = quote_plus(str(Config.DB_PASSWORD_PROMPT))
            db_url = f"postgresql://{Config.DB_USER_PROMPT}:{password}@{Config.DB_HOST_PROMPT}:{Config.DB_PORT_PROMPT}/{Config.DB_DATABASE_PROMPT}"
            engine = create_engine(db_url)

            with engine.begin() as connection:
                # 사용하려는 스키마 지정
                connection.execute(text("SET search_path TO '%s'" % Config.DB_SCHEMA_PROMPT))

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
                    'question': question_str,  # 변환된 문자열 사용
                    'model': model
                })

            return qna_id

        except Exception as e:
            print(f"Error in create_question: {str(e)}")
            raise

    def record_answer(self, qna_id: str, answer: str) -> bool:
        """
        LLM 응답을 받은 시점에 답변 기록
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