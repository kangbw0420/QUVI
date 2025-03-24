import re
import uuid
from typing import Any

from sqlalchemy import create_engine, text
from langchain_core.prompts import ChatPromptTemplate
from urllib.parse import quote_plus

from utils.config import Config
from core.postgresql import query_execute
from utils.logger import setup_logger

logger = setup_logger('qna')


class QnAManager:
    def format_message_str(self, msg_str: str) -> str:
        """ChatPromptTemplate의 메시지 문자열을 role과 content로 파싱하여 포맷팅
        Args:
            msg_str: ChatPromptTemplate의 messages 속성을 str로 변환한 문자열
        Returns:
            'role\ncontent' 형식의 문자열들을 개행 2번으로 구분하여 연결한 문자열
        """
        messages = []

        # 전체 메시지를 블록 단위로 추출
        pattern = r"(SystemMessage\(.*?\)|HumanMessagePromptTemplate\(.*?\)|AIMessagePromptTemplate\(.*?\))"
        matches = re.findall(pattern, msg_str, re.DOTALL)

        for match in matches:
            if match.startswith("SystemMessage"):
                role = "system"
                content_match = re.search(r"content=['\"](.*?)['\"]\)?$", match, re.DOTALL)
            elif match.startswith("HumanMessagePromptTemplate"):
                role = "user"
                content_match = re.search(r"template=['\"](.*?)['\"]\)?$", match, re.DOTALL)
            elif match.startswith("AIMessagePromptTemplate"):
                role = "assistant"
                content_match = re.search(r"template=['\"](.*?)['\"]\)?$", match, re.DOTALL)
            else:
                continue

            if content_match:
                content = content_match.group(1)
                messages.append(f"{role}\n{content.strip()}")

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

            logger.info(question_str)

            query = """
                INSERT INTO qna (
                    id,
                    trace_id,
                    question,
                    model
                ) VALUES (
                    %(qna_id)s,
                    %(trace_id)s,
                    %(question)s,
                    %(model)s
                )
            """
            params = {
                'qna_id': qna_id,
                'trace_id': trace_id,
                'question': question_str,
                'model': model
            }

            query_execute(query, params, use_prompt_db=True)
            return qna_id

        except Exception as e:
            logger.info(f"Error in create_question: {str(e)}")
            raise

    def record_answer(self, qna_id: str, answer: str) -> bool:
        """
        LLM 응답을 받은 시점에 답변 기록
        Returns:
            bool: 성공 여부
        """
        try:
            query = """
                UPDATE qna 
                SET 
                    answer = %(answer)s,
                    answer_timestamp = CURRENT_TIMESTAMP
                WHERE id = %(qna_id)s
            """
            params = {
                'qna_id': qna_id,
                'answer': answer
            }

            return query_execute(query, params, use_prompt_db=True)

        except Exception as e:
            logger.info(f"Error in record_answer: {str(e)}")
            raise