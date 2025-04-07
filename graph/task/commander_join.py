from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core.postgresql import get_prompt
from graph.models import qwen_llm
from utils.retriever import retriever
from llm_admin.qna_manager import QnAManager
from utils.logger import setup_logger

qna_manager = QnAManager()
logger = setup_logger('commander')

async def command_join(trace_id: str, user_question: str) -> str:
    """사용자의 질문으로부터 테이블을 선택
    Returns:
        str: 'aicfo_get_all_XXXX'의 테이블
    Raises:
        ValueError: 질문이 분석 가능한 형식이 아닌 경우.
    """
    output_parser = StrOutputParser()

    system_prompt = get_prompt(node_nm='commander', prompt_nm='join')[0]['prompt']

    few_shots = await retriever.get_few_shots(
        query_text=user_question,
        collection_name="commander_join",
        top_k=5
    )
    few_shot_prompt = []
    for example in reversed(few_shots):
        if "stats" in example:
            human_with_stats = f'사용자의 질문:\n{example["input"]}\n\n사용 가능한 column_nm:\n{example["stats"]}'
            few_shot_prompt.append(("human", human_with_stats))
        else:
            few_shot_prompt.append(("human", example["input"]))
        few_shot_prompt.append(("ai", example["output"]))

    human_prompt = get_prompt(node_nm='respondent', prompt_nm='human')[0]['prompt'].format(
        user_question=user_question
    )

    COMMANDER_PROMPT = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            *few_shot_prompt,
            ("human", user_question)
        ]
    )

    logger.debug("===== commander_join(Q) =====")
    qna_id = qna_manager.create_question(
        trace_id=trace_id,
        question=COMMANDER_PROMPT,
        model="qwen_llm"
    )

    commander_chain = COMMANDER_PROMPT | qwen_llm | output_parser
    selected_table = commander_chain.invoke({"user_question": user_question})

    logger.debug("===== commander_join(A) =====")
    logger.info(f"Selected table: {selected_table}")
    qna_manager.record_answer(qna_id, selected_table)

    return selected_table