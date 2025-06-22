import json
from typing import List

from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core.postgresql import get_prompt
from graph.models import selector
from utils.retriever import retriever
from llm_admin.qna_manager import QnAManager
from utils.logger import setup_logger

qna_manager = QnAManager()
logger = setup_logger('commander')

async def command(trace_id: str, user_question: str) -> str:
    output_parser = StrOutputParser()

    system_prompt = get_prompt(node_nm='commander', prompt_nm='system')[0]['prompt']

    few_shots = await retriever.get_few_shots(
        query_text=user_question,
        collection_name="shots_selector",
        top_k=5
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

    logger.debug("===== commander(Q) =====")
    qna_id = qna_manager.create_question(
        trace_id=trace_id,
        question=COMMANDER_PROMPT,
        model="qwen_selector"
    )

    commander_chain = COMMANDER_PROMPT | selector | output_parser
    
    selected_table = commander_chain.invoke({"user_question": user_question})
    
    logger.debug("===== commander(A) =====")
    logger.info(f"selected_table : {selected_table}")
    qna_manager.record_answer(qna_id, selected_table)

    return selected_table