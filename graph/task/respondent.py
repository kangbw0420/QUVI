from typing import Optional, Tuple

from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from graph.models import solver, qwen_llm
from graph.prompts.prompts_core import PROMPT_RESPONDENT_HUMAN, PROMPT_RESPONDENT_SYSTEM, PROMPT_PAGE_RESPONDENT_SYSTEM
from llm_admin.qna_manager import QnAManager
from utils.common.llm_output_handler import handle_python_code_block
from utils.fstring.fstring_assistant import pipe_table
from utils.logger import setup_logger
from utils.retriever import retriever

qna_manager = QnAManager()
logger = setup_logger("respondent")


async def paginated_response(
        trace_id: str,
        user_question: str,
        total_rows: int = 0,
        respondent_history: dict = {}
) -> str:
    try:
        output_parser = StrOutputParser()
        system_prompt = PROMPT_PAGE_RESPONDENT_SYSTEM.format(
            total_rows=total_rows)

        qna_id = qna_manager.create_qna_id(trace_id)

        chat_history_prompt = []
        for history_list in respondent_history.values():
            for history_item in history_list:
                if all(
                        key in history_item
                        for key in ["user_question", "final_answer"]
                ) and all(
                    history_item[key]
                    for key in ["user_question", "final_answer"]
                ):
                    chat_history_prompt.append(
                        ("human", history_item["user_question"]))
                    chat_history_prompt.append(
                        ("ai", history_item["final_answer"]))

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_prompt),
                *chat_history_prompt,
                ("human", user_question),
            ]
        )

        logger.info("===== table_respondent(Q) =====")
        qna_manager.update_question(
            qna_id=qna_id,
            question=prompt,
            model="qwen_14b"
        )

        chain = prompt | qwen_llm | output_parser
        answer = chain.invoke({"human_prompt": user_question})

        logger.info("===== table_respondent(A) =====")
        logger.info(f"Answer content: {answer}")
        qna_manager.record_answer(qna_id, answer)

        return answer

    except Exception:
        logger.exception("paginated_response() 실행 중 예외 발생")


async def response(
        trace_id: str,
        user_question,
        date_info: Optional[Tuple[str, str]] = None,
        query_result: list = [],
        respondent_history: dict = {},
) -> Tuple[str, str]:
    """쿼리 실행 결과를 바탕으로 자연어 응답을 생성합니다."""

    fstring_answer = "응답 생성 중 오류가 발생했습니다."

    try:
        output_parser = StrOutputParser()

        # 시스템 메시지만 사용 (퓨샷과 분리)
        system_prompt = PROMPT_RESPONDENT_SYSTEM

        # 퓨샷 예제 가져오기
        few_shots, retrieve_time = await retriever.get_few_shots(
            query_text=user_question, collection_name="shots_respondent_table", top_k=5
        )

        qna_id = qna_manager.create_qna_id(trace_id)

        # 테이블 파이프 생성
        if (
                isinstance(query_result, tuple)
                and len(query_result) == 2
                and isinstance(query_result[0], list)
        ):
            data_for_table = query_result[0]
        else:
            data_for_table = query_result

        table_pipe = pipe_table(data_for_table)

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

        # 현재 사용자의 human 메시지 구성
        human_prompt = PROMPT_RESPONDENT_HUMAN.format(
            table_pipe=table_pipe, user_question=formatted_user_question
        )

        # 프롬프트 메시지 리스트 구성
        messages = [
            SystemMessage(content=system_prompt)  # 1. 시스템 메시지
        ]

        # 2. 퓨샷 예제들 (human/ai 쌍으로 추가)
        for order, example in enumerate(reversed(few_shots), 1):
            if "stats" in example:
                if "date" in example:
                    human_with_stats_date = (
                        f"결과 데이터:\n{example['stats']}\n\n"
                        f"사용자의 질문:\n{example['date']}. {example['input']}"
                    )
                    messages.append(("human", human_with_stats_date))
                else:
                    human_with_stats = f"결과 데이터:\n{example['stats']}\n\n사용자의 질문:\n{example['input']}"
                    messages.append(("human", human_with_stats))
            else:
                messages.append(("human", example["input"]))
            messages.append(("ai", example["output"]))

            # Few-shot 예제 저장
            qna_manager.record_fewshot(
                qna_id=qna_id,
                retrieved=example["input"],
                human=human_with_stats_date if "stats" in example and "date" in example else
                human_with_stats if "stats" in example else example["input"],
                ai=example["output"],
                order=order
            )

        # 3. 대화 히스토리 (human/ai 쌍으로 추가)
        for history_list in respondent_history.values():
            for history_item in history_list:
                if all(
                        key in history_item
                        for key in ["user_question", "table_pipe", "fstring_answer"]
                ) and all(
                    history_item[key]
                    for key in ["user_question", "table_pipe", "fstring_answer"]
                ):
                    human_message = f"결과 데이터:\n{history_item['table_pipe']}\n\n사용자의 질문:\n{history_item['user_question']}"
                    messages.append(("human", human_message))
                    messages.append(("ai", history_item["fstring_answer"]))

        # 4. 현재 사용자 질문
        messages.append(("human", human_prompt))

        # ChatPromptTemplate 생성
        prompt = ChatPromptTemplate.from_messages(messages)

        logger.info("===== table_respondent(Q) =====")
        qna_manager.update_question(
            qna_id=qna_id,
            question=prompt,
            model="qwen_14b"
        )

        chain = prompt | solver | output_parser
        raw_answer = chain.invoke({"human_prompt": user_question})

        # 코드 블록 마커 제거
        fstring_answer = handle_python_code_block(raw_answer)

        logger.info("===== table_respondent(A) =====")
        logger.info(f"Answer content: {fstring_answer}")
        qna_manager.record_answer(qna_id, fstring_answer, retrieve_time)

    except Exception:
        logger.exception("response() 실행 중 예외 발생")

    return fstring_answer, table_pipe
