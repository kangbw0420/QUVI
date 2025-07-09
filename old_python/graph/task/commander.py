from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from utils.common.llm_output_handler import handle_ai_colon
from graph.prompts.prompts_guardian import PROMPT_COMMANDER
from graph.models import selector
from utils.retriever import retriever
from llm_admin.qna_manager import QnAManager
from utils.logger import setup_logger
from utils.common.chat_history import convert_to_chat_history

qna_manager = QnAManager()
logger = setup_logger('commander')

async def command(trace_id: str, user_question: str, commander_history: dict) -> str:
    output_parser = StrOutputParser()

    few_shots, retrieve_time = await retriever.get_few_shots(
        query_text=user_question,
        collection_name="shots_selector",
        top_k=5
    )
    # few_shot_prompt = []
    # for example in reversed(few_shots):
    #     few_shot_prompt.append(("human", example["input"]))
    #     few_shot_prompt.append(("ai", example["output"]))

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

    flattend_few_shot_prompt = "\n".join(
        f"{role}: {text}" for role, text in few_shot_prompt
    )
    concat_few_shot_prompt = f"{PROMPT_COMMANDER}\n{flattend_few_shot_prompt}"

    chat_history_prompt = convert_to_chat_history(
        commander_history,
        required_fields=["user_question", "selected_table"],
        human_field="user_question",
        ai_field="selected_table"
    )

    commander_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=PROMPT_COMMANDER),
            *few_shot_prompt,
            ("human", user_question)
        ]
    )

    qna_manager.update_question(
        qna_id=qna_id,
        question=commander_prompt,
        model="qwen_14b"
    )

    commander_chain = commander_prompt | selector | output_parser

    selected_table = commander_chain.invoke({"user_question": user_question})
    selected_table = handle_ai_colon(selected_table)
    logger.info(f"selected_table : {selected_table}")
    qna_manager.record_answer(qna_id, selected_table, retrieve_time)

    return selected_table
