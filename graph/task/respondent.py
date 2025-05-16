from typing import Optional, Tuple

from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from graph.models import solver
from graph.prompts.prompts_core import PROMPT_RESPONDENT_HUMAN, PROMPT_RESPONDENT_SYSTEM
from utils.retriever import retriever
from utils.table.format_table import format_table_pipe
from llm_admin.qna_manager import QnAManager
from utils.logger import setup_logger

qna_manager = QnAManager()
logger = setup_logger("respondent")


async def response(
    trace_id: str,
    user_question,
    date_info: Optional[Tuple[str, str]] = None,
    query_result=None,
    chat_history_prompt: list[tuple[str, str]] = [],
) -> str:
    """쿼리 실행 결과를 바탕으로 자연어 응답을 생성합니다."""

    fstring_answer = "응답 생성 중 오류가 발생했습니다."  # 예외 발생 시 기본 응답

    try:
        output_parser = StrOutputParser()

        result = query_result or []

        system_prompt = PROMPT_RESPONDENT_SYSTEM

        few_shots = await retriever.get_few_shots(
            query_text=user_question, collection_name="shots_respondent_table", top_k=5
        )
        few_shot_prompt = []
        for example in reversed(few_shots):
            if "stats" in example:
                # 날짜 정보가 있는 경우와 없는 경우를 구분
                if "date" in example:
                    human_with_stats_date = (
                        f'결과 데이터:\n{example["stats"]}\n\n'
                        f'사용자의 질문:\n{example["date"]}. {example["input"]}'
                    )
                    few_shot_prompt.append(("human", human_with_stats_date))
                else:
                    human_with_stats = f'결과 데이터:\n{example["stats"]}\n\n사용자의 질문:\n{example["input"]}'
                    few_shot_prompt.append(("human", human_with_stats))
            else:
                few_shot_prompt.append(("human", example["input"]))
            few_shot_prompt.append(("ai", example["output"]))

        logger.info(f"Generated respondent few-shot examples: {few_shot_prompt}")
        logger.info(f"Generated result: {result}")

        if (
            isinstance(result, tuple)
            and len(result) == 2
            and isinstance(result[0], list)
        ):
            data_for_table = result[0]
        else:
            data_for_table = result

        table_pipe = format_table_pipe(data_for_table)

        logger.info(f"Generated table pipe format:\n{table_pipe}")

        # 사용자 질문에 날짜 정보 추가
        formatted_user_question = user_question
        if date_info and isinstance(date_info, tuple) and len(date_info) == 2:
            try:
                from_date, to_date = date_info
                if from_date and to_date:
                    formatted_from = f"{from_date[:4]}년 {int(from_date[4:6])}월 {int(from_date[6:8])}일"
                    formatted_to = (
                        f"{to_date[:4]}년 {int(to_date[4:6])}월 {int(to_date[6:8])}일"
                    )
                    formatted_user_question = f"시작 시점: {formatted_from}, 종료 시점: {formatted_to}. {user_question}"
            except Exception as e:
                logger.warning(f"Failed to format date info: {str(e)}")

        human_prompt = PROMPT_RESPONDENT_HUMAN.format(
            table_pipe=table_pipe, user_question=formatted_user_question
        )

        # 시스템 메시지와 퓨샷 합치기
        flattend_few_shot_prompt = "\n".join(
            f"{role}: {text}" for role, text in few_shot_prompt
        )
        concat_few_shot_prompt = f"{system_prompt}\n{flattend_few_shot_prompt}"

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=concat_few_shot_prompt),
                *chat_history_prompt,
                ("human", human_prompt),
            ]
        )
        logger.debug("===== table_respondent(Q) =====")
        qna_id = qna_manager.create_question(
            trace_id=trace_id, question=prompt, model="qwen_14b"
        )

        chain = prompt | solver | output_parser
        raw_answer = chain.invoke({"human_prompt": user_question})

        # 코드 블록 마커 제거
        fstring_answer = raw_answer.strip()
        if fstring_answer.startswith("```python\n"):
            fstring_answer = fstring_answer[10:]
        elif fstring_answer.startswith("```python"):
            fstring_answer = fstring_answer[9:]

        if fstring_answer.endswith("\n```"):
            fstring_answer = fstring_answer[:-4]
        elif fstring_answer.endswith("```"):
            fstring_answer = fstring_answer[:-3]

        logger.debug("===== table_respondent(A) =====")
        logger.info(f"Answer content: {fstring_answer}")
        qna_manager.record_answer(qna_id, fstring_answer)

    except Exception as e:
        logger.exception("response() 실행 중 예외 발생")

    return fstring_answer, table_pipe, human_prompt
