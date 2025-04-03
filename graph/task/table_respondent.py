import json
import os
from typing import Optional, Tuple
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core.postgresql import get_prompt
from graph.models import solver
from utils.table.main_table import evaluate_fstring_template
from utils.retriever import retriever
from utils.table.format_table import format_table_pipe
from llm_admin.qna_manager import QnAManager
from utils.logger import setup_logger
from rapidfuzz import fuzz, process

qna_manager = QnAManager()
logger = setup_logger('respondent')


async def response(trace_id: str, user_question, selected_table: str, column_list=None,
                   date_info: Optional[Tuple[str, str]] = None , query_result = None) -> str:
    """쿼리 실행 결과를 바탕으로 자연어 응답을 생성합니다."""

    final_response = "응답 생성 중 오류가 발생했습니다."  # 예외 발생 시 기본 응답

    try:
        output_parser = StrOutputParser()
        logger.info(f"Generating table response for question: {user_question[:50]}...")

        logger.debug(f"Query result type: {type(query_result)}")
        logger.debug(f"Query result size: {len(query_result) if query_result else 0}")
        logger.debug(f"Column list: {column_list}")

        result = query_result or []
        cols = column_list or []

        # 간단한 프롬프트로 시작
        simple_prompt = """
        당신은 사용자의 재무 데이터 조회 질문에 대해, 주어진 DataFrame을 기반으로 f-string 형태의 자연어 답변을 생성하는 전문가입니다.
        사용자의 질문을 그대로 응답하지 말고 사용자 질문과 주어진 결과 데이터를 활용하여 정확한 f-string 기반 답변 문장 한 줄을 생성하세요.
        """

        if selected_table == 'api':
            collection_name = "shots_respondent_api"
        else:
            collection_name = "shots_respondent_sql"

        few_shots = await retriever.get_few_shots(
            query_text=user_question,
            collection_name=collection_name,
            top_k=5
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
        table_pipe = format_table_pipe(result, cols)
        logger.info(f"Created data table from query results")

        # 표 형식 데이터의 로그 확인
        logger.info(f"Generated table pipe format:\n{table_pipe}")

        # 사용자 질문에 날짜 정보 추가
        formatted_user_question = user_question
        if date_info and isinstance(date_info, tuple) and len(date_info) == 2:
            try:
                from_date, to_date = date_info
                if from_date and to_date:
                    formatted_from = f"{from_date[:4]}년 {int(from_date[4:6])}월 {int(from_date[6:8])}일"
                    formatted_to = f"{to_date[:4]}년 {int(to_date[4:6])}월 {int(to_date[6:8])}일"
                    formatted_user_question = f"시작 시점: {formatted_from}, 종료 시점: {formatted_to}. {user_question}"
            except Exception as e:
                logger.warning(f"Failed to format date info: {str(e)}")

        # 최종 프롬프트 구성
        human_prompt = f"""결과 데이터:
        {table_pipe}
        
        사용자의 질문:
        {formatted_user_question}
        
        컬럼 설명:
        {', '.join(cols)}
        """

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=simple_prompt),
                *few_shot_prompt,
                ("human", human_prompt)
            ]
        )
        logger.debug("===== table_respondent(Q) =====")
        qna_id = qna_manager.create_question(
            trace_id=trace_id,
            question=prompt,
            model="qwen_14b"
        )

        chain = prompt | solver | output_parser
        raw_answer = chain.invoke({"human_prompt": user_question})

        # 코드 블록 마커 제거
        fstring_answer = raw_answer.strip()
        if fstring_answer.startswith('```python\n'):
            fstring_answer = fstring_answer[10:]
        elif fstring_answer.startswith('```python'):
            fstring_answer = fstring_answer[9:]

        if fstring_answer.endswith('\n```'):
            fstring_answer = fstring_answer[:-4]
        elif fstring_answer.endswith('```'):
            fstring_answer = fstring_answer[:-3]

        logger.debug("===== table_respondent(A) =====")
        logger.info(f"Generated table answer (length: {len(fstring_answer)})")
        logger.info(f"Answer content: {fstring_answer}")
        qna_manager.record_answer(qna_id, fstring_answer)

        # ✅ f-string 평가 수행
        final_response = evaluate_fstring_template(fstring_answer, result)

    except Exception as e:
        logger.exception("response() 실행 중 예외 발생")

    return table_pipe, final_response