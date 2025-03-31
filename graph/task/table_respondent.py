from typing import Optional, Tuple
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core.postgresql import get_prompt
from graph.models import solver
from utils.compute.main_compute import evaluate_fstring_template
from utils.retriever import retriever
from llm_admin.qna_manager import QnAManager
from utils.logger import setup_logger

qna_manager = QnAManager()
logger = setup_logger('respondent')

async def response(trace_id: str, user_question, column_list=None,
                   date_info: Optional[Tuple[str, str]] = None, query_result=None) -> str:
    """쿼리 실행 결과를 바탕으로 자연어 응답을 생성합니다."""
    try:
        output_parser = StrOutputParser()
        logger.info(f"Generating table response for question: {user_question[:50]}...")

        # 데이터 로깅
        logger.debug(f"Query result type: {type(query_result)}")
        logger.debug(f"Query result size: {len(query_result) if query_result else 0}")
        logger.debug(f"Column list: {column_list}")

        # 결과가 없으면 빈 리스트로 설정
        result = query_result or []
        cols = column_list or []

        # 간단한 프롬프트로 시작
        simple_prompt ="""
        당신은 사용자의 재무 데이터 조회 질문에 대해, 주어진 DataFrame을 기반으로 f-string 형태의 자연어 응답을 생성하는 전문가입니다.

        다음 제약을 반드시 지켜야 합니다:

        1. DataFrame의 값을 직접 텍스트로 출력하지 말고, 반드시 pandas indexing을 활용한 f-string 표현으로 작성해야 합니다.

        2. DataFrame 컬럼에 접근할 때는 반드시 df[\'컬럼명\'] 또는 df.loc[...] 형식을 사용해야 하며,
           bank_nm, real_amt 같은 컬럼명을 단독 변수처럼 사용해서는 안 됩니다.

        3. 주어진 데이터에 존재하지 않는 정보나 컬럼은 포함하지 마세요.

        4. 답변은 한글로 된 간결하고 완성된 문장이어야 하며, f-string 이외의 설명 또는 주석은 허용되지 않습니다.
        
        5. 사용자가 비교 데이터를 원할 경우 직접 정답을 생성하지 말고, 주어진 데이터를 통해 정답을 도출하는 f-string 문장을 만들어주세요.
        
        6. 날짜나 항목 간 비교 결과를 문장에 포함시킬 때는 f-string 안에서 if-else 조건문을 사용할 수 있습니다.
            - 조건 비교는 숫자 컬럼의 개수나 합계 등을 기준으로 할 수 있습니다.
            - 반드시 f-string 내부에서 표현식을 완결된 문장으로 작성해야 하며, 조건 분기는 한 문장 안에서 처리해야 합니다.
            - 한 문장 안에 비교 결과를 자연스럽게 녹여야 하며, 조건은 숫자 기반으로 작성하세요.
        
        7. f-string 표현식 안에 다시 f-string을 중첩하지 마세요. 바깥쪽 f"..."는 제거하고 내부 표현식만 중괄호로 감싸야 합니다.
        """

        table_pipe = format_table_pipe(result, cols)
        logger.info(f"Created data table from query results")

        # 표 형식 데이터의 로그 확인
        logger.debug(f"Generated table pipe format:\n{table_pipe}")

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
                ("human", human_prompt),
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
        logger.info(f"Final response: {final_response}")

    finally:
        return final_response