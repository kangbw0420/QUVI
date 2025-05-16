from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from graph.models import qwen_llm
from graph.prompts.prompts_api import PROMPT_FUNK
from utils.logger import setup_logger
from utils.retriever import retriever
from llm_admin.qna_manager import QnAManager

qna_manager = QnAManager()

# 모듈 상단에 로거 정의
logger = setup_logger("funk")


async def func_select(
    trace_id: str, user_question: str, chat_history_prompt: list[tuple[str, str]]
) -> str:
    """사용자의 질문으로부터 테이블을 선택
    Returns:
        str: 'aicfo_get_xxxx'의 테이블 (예: aicfo_get_financial_status)
    Raises:
        ValueError: 질문이 분석 가능한 형식이 아닌 경우.
    """
    output_parser = StrOutputParser()

    few_shots = await retriever.get_few_shots(
        query_text=user_question, collection_name="shots_api_selector", top_k=5
    )
    few_shot_prompt = []
    for example in reversed(few_shots):
        few_shot_prompt.append(("human", example["input"]))
        few_shot_prompt.append(("ai", example["output"]))

    # 시스템 메시지와 퓨샷 합치기
    flattend_few_shot_prompt = "\n".join(
        f"{role}: {text}" for role, text in few_shot_prompt
    )
    concat_few_shot_prompt = f"{PROMPT_FUNK}\n{flattend_few_shot_prompt}"

    FUNK_PROMPT = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=concat_few_shot_prompt),
            *chat_history_prompt,
            ("human", user_question),
        ]
    )

    # print 대신 logger 사용
    logger.debug("===== funk(Q) =====")
    qna_id = qna_manager.create_question(
        trace_id=trace_id, question=FUNK_PROMPT, model="qwen_14b"
    )

    funk_chain = FUNK_PROMPT | qwen_llm | output_parser
    funk = funk_chain.invoke({"user_question": user_question})

    logger.debug("===== funk(A) =====")
    logger.info(funk)
    qna_manager.record_answer(qna_id, funk)

    return funk
