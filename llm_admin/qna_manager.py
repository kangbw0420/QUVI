import uuid
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from core.postgresql import query_execute
from utils.logger import setup_logger

logger = setup_logger('qna')


class QnAManager:
    def format_message_str(self, msg_str: str) -> str:
        # 연속된 개행문자를 하나로 통일하고 앞뒤 공백 제거
        return msg_str.replace('\\n', '\n').strip()

    def create_qna_id(self, trace_id: str) -> str:
        """QnA ID를 생성하고 기본 레코드를 생성합니다.
        Args:
            trace_id: 추적 ID
        Returns:
            str: 생성된 qna_id
        """
        try:
            qna_id = str(uuid.uuid4())
            query = """
                INSERT INTO qna (
                    id,
                    trace_id
                ) VALUES (
                    %(qna_id)s,
                    %(trace_id)s
                )
            """
            params = {
                'qna_id': qna_id,
                'trace_id': trace_id
            }
            query_execute(query, params, use_prompt_db=True)
            return qna_id
        except Exception as e:
            logger.error(f"Error in create_qna_id: {str(e)}")
            raise

    def record_fewshot(self, qna_id: str, retrieved: str, human: str, ai: str, order: int) -> bool:
        """단일 Few-shot 예제를 저장합니다.
        Args:
            qna_id: QnA ID
            retrieved: 벡터 스토어에서 검색된 원본 질문
            human: 실제 사용된 human prompt
            ai: AI 응답
            order: 순서
        Returns:
            bool: 성공 여부
        """
        try:
            fewshot_id = str(uuid.uuid4())
            query = """
                INSERT INTO fewshot (
                    id,
                    qna_id,
                    fewshot_retrieved,
                    fewshot_human,
                    fewshot_ai,
                    order_seq
                ) VALUES (
                    %(fewshot_id)s,
                    %(qna_id)s,
                    %(retrieved)s,
                    %(human)s,
                    %(ai)s,
                    %(order)s
                )
            """
            params = {
                'fewshot_id': fewshot_id,
                'qna_id': qna_id,
                'retrieved': retrieved,
                'human': human,
                'ai': ai,
                'order': order
            }
            return query_execute(query, params, use_prompt_db=True)
        except Exception as e:
            logger.error(f"Error in record_fewshot: {str(e)}")
            raise

    def update_question(self, qna_id: str, question: Any, model: str) -> bool:
        """QnA 레코드에 질문과 모델 정보를 업데이트합니다.
        Args:
            qna_id: QnA ID
            question: 질문 (ChatPromptTemplate 또는 str)
            model: 모델명
        Returns:
            bool: 성공 여부
        """
        try:
            # ChatPromptTemplate인 경우 문자열로 변환
            if isinstance(question, ChatPromptTemplate):
                question_str = self.format_message_str(str(question.messages))
            else:
                question_str = str(question)

            query = """
                UPDATE qna 
                SET 
                    question = %(question)s,
                    model = %(model)s
                WHERE id = %(qna_id)s
            """
            params = {
                'qna_id': qna_id,
                'question': question_str,
                'model': model
            }
            return query_execute(query, params, use_prompt_db=True)
        except Exception as e:
            logger.error(f"Error in update_question: {str(e)}")
            raise

    def record_answer(self, qna_id: str, answer: str, retrieve_time: float = None) -> bool:
        """LLM 응답을 받은 시점에 답변 기록
        Returns:
            bool: 성공 여부
        """
        try:
            query = """
                UPDATE qna 
                SET 
                    answer = %(answer)s,
                    answer_timestamp = CURRENT_TIMESTAMP,
                    retrieve_time = %(retrieve_time)s
                WHERE id = %(qna_id)s
            """
            params = {
                'qna_id': qna_id,
                'answer': answer,
                'retrieve_time': retrieve_time
            }
            return query_execute(query, params, use_prompt_db=True)
        except Exception as e:
            logger.error(f"Error in record_answer: {str(e)}")
            raise