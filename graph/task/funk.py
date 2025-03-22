from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core.postgresql import get_prompt
from graph.models import qwen_llm
from utils.logger import setup_logger
from utils.retriever import retriever
from llm_admin.qna_manager import QnAManager

qna_manager = QnAManager()

# 모듈 상단에 로거 정의
logger = setup_logger('funk')

async def func_select(trace_id: str, user_question: str) -> str:
    """사용자의 질문으로부터 테이블을 선택
    Returns:
        str: 'aicfo_get_xxxx'의 테이블 (예: aicfo_get_financial_status)
    Raises:
        ValueError: 질문이 분석 가능한 형식이 아닌 경우.
    """
    output_parser = StrOutputParser()

    system_prompt = get_prompt(
        node_nm="funk", prompt_nm="system"
    )[0]["prompt"]

    few_shots = await retriever.get_few_shots(
        query_text=user_question, collection_name="shots_api_selector", top_k=5
    )
    few_shot_prompt = []
    for example in reversed(few_shots):
        few_shot_prompt.append(("human", example["input"]))
        few_shot_prompt.append(("ai", example["output"]))

    FUNK_PROMPT = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            *few_shot_prompt,
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