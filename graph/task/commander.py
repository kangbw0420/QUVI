from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from database.database_service import DatabaseService
from graph.models import selector
from utils.retriever import retriever
from llm_admin.qna_manager import QnAManager
from utils.logger import setup_logger

database_service = DatabaseService()
qna_manager = QnAManager()
logger = setup_logger('commander')

async def command(trace_id: str, user_question: str) -> str:
    """사용자의 질문으로부터 테이블을 선택
    Returns:
        str: 'aicfo_get_all_XXXX'의 테이블
    Raises:
        ValueError: 질문이 분석 가능한 형식이 아닌 경우.
    """
    output_parser = StrOutputParser()

    system_prompt = database_service.get_prompt(node_nm='commander', prompt_nm='system')[0]['prompt']

    few_shots = await retriever.get_few_shots(
        query_text=user_question, collection_name="shots_selector", top_k=5
    )
    few_shot_prompt = []
    for example in reversed(few_shots):
        few_shot_prompt.append(("human", example["input"]))
        few_shot_prompt.append(("ai", example["output"]))

    COMMANDER_PROMPT = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            *few_shot_prompt,
            ("human", user_question)
        ]
    )

    logger.debug("===== selector(Q) =====")
    qna_id = qna_manager.create_question(
        trace_id=trace_id,
        question=COMMANDER_PROMPT,
        model="qwen_selector"
    )

    commander_chain = COMMANDER_PROMPT | selector | output_parser
    selected_table = commander_chain.invoke({"user_question": user_question})

    logger.debug("===== selector(A) =====")
    logger.info(f"Selected table: {selected_table}")
    qna_manager.record_answer(qna_id, selected_table)

    return selected_table