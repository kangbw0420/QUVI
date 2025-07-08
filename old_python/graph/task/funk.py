from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from graph.models import qwen_llm
from graph.prompts.prompts_api import PROMPT_FUNK
from utils.common.llm_output_handler import handle_ai_colon
from utils.logger import setup_logger
from utils.retriever import retriever
from utils.common.chat_history import convert_to_chat_history
from llm_admin.qna_manager import QnAManager


qna_manager = QnAManager()

# 모듈 상단에 로거 정의
logger = setup_logger("funk")


async def func_select(
    trace_id: str,
    user_question: str,
    funk_history: dict
) -> str:
    """사용자의 질문으로부터 테이블을 선택
    Args:
        trace_id: 추적 ID
        user_question: 사용자 질문
        funk_history: chain_id별로 그룹화된 과거 대화 이력
    Returns:
        str: 'aicfo_get_xxxx'의 테이블 (예: aicfo_get_financial_status)
    Raises:
        ValueError: 질문이 분석 가능한 형식이 아닌 경우.
    """
    output_parser = StrOutputParser()

    few_shots, retrieve_time = await retriever.get_few_shots(
        query_text=user_question, collection_name="shots_api_selector", top_k=5
    )

    qna_id = qna_manager.create_qna_id(trace_id)

    few_shot_prompt = []
    for order, example in enumerate(reversed(few_shots), 1):
        few_shot_prompt.append(("human", example["input"]))
        few_shot_prompt.append(("ai", example["output"]))

        # Few-shot 예제 저장
        qna_manager.record_fewshot(
            qna_id=qna_id,
            retrieved=example["input"],
            human=example["input"],
            ai=example["output"],
            order=order
        )

    # 시스템 메시지와 퓨샷 합치기
    flattend_few_shot_prompt = "\n".join(
        f"{role}: {text}" for role, text in few_shot_prompt
    )
    concat_few_shot_prompt = f"{PROMPT_FUNK}\n{flattend_few_shot_prompt}"

    # Convert funk_history to chat_history_prompt format
    chat_history_prompt = convert_to_chat_history(
        funk_history,
        required_fields=["user_question", "selected_api"],
        human_field="user_question",
        ai_field="selected_api"
    )

    FUNK_PROMPT = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=concat_few_shot_prompt),
            *chat_history_prompt,
            ("human", user_question),
        ]
    )

    # print 대신 logger 사용
    logger.info("===== funk(Q) =====")
    qna_manager.update_question(
        qna_id=qna_id,
        question=FUNK_PROMPT,
        model="qwen_14b"
    )

    funk_chain = FUNK_PROMPT | qwen_llm | output_parser
    funk = funk_chain.invoke({"user_question": user_question})
    funk = handle_ai_colon(funk)

    logger.info("===== funk(A) =====")
    logger.info(funk)
    qna_manager.record_answer(qna_id, funk, retrieve_time)

    return funk
