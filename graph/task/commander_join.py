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

    # few_shots = await retriever.get_few_shots(
    #     query_text=user_question, collection_name="commander_join", top_k=5
    # )
    # few_shot_prompt = []
    # for example in reversed(few_shots):
    #     few_shot_prompt.append(("human", example["input"]))
    #     few_shot_prompt.append(("ai", example["output"]))

    few_shots = await retriever.get_few_shots(
        query_text=user_question,
        collection_name=collection_name,
        top_k=3
    )
    few_shot_prompt = []
    for example in reversed(few_shots):
        if "stats" in example:
            # 날짜 정보가 있는 경우와 없는 경우를 구분
            if "date" in example:
                human_with_stats_date = (
                    f'사용 가능한 column_nm:\n{example["stats"]}\n\n'
                    f'사용자의 질문:\n{example["date"]}. {example["input"]}'
                )
                few_shot_prompt.append(("human", human_with_stats_date))
            else:
                human_with_stats = f'사용 가능한 column_nm:\n{example["stats"]}\n\n사용자의 질문:\n{example["input"]}'
                few_shot_prompt.append(("human", human_with_stats))
        else:
            few_shot_prompt.append(("human", example["input"]))
        few_shot_prompt.append(("ai", example["output"]))

    # column_list를 문자열로 변환
    column_list_str = ", ".join(column_list) if column_list else ""

    if date_info:
        (from_date, to_date) = date_info
        try:
            formatted_from = f"{from_date[:4]}년 {int(from_date[4:6])}월 {int(from_date[6:8])}일"
            formatted_to = f"{to_date[:4]}년 {int(to_date[4:6])}월 {int(to_date[6:8])}일"
            formatted_user_question = f"시작 시점: {formatted_from}, 종료 시점: {formatted_to}. {user_question}"
        except:
            formatted_user_question = f"시작 시점: {from_date}, 종료 시점: {to_date}. {user_question}"
            logger.warning(f"Failed to format date info: {from_date}, {to_date}")
    else:
        formatted_user_question = user_question

    human_prompt = get_prompt(node_nm='respondent', prompt_nm='human')[0]['prompt'].format(
        column_list=column_list_str, user_question=formatted_user_question
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            *few_shot_prompt,
            ("human", human_prompt),
        ]
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