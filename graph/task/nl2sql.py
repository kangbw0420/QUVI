import re
from datetime import datetime

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from graph.models import nl2sql
from graph.prompts.prompts_core import PROMPT_NL2SQL
from utils.retriever import retriever
from llm_admin.qna_manager import QnAManager
from utils.logger import setup_logger

qna_manager = QnAManager()
logger = setup_logger("nl2sql")

WEEKDAYS = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}


async def create_sql(
    trace_id: str,
    company_id: str,
    user_question: str,
    chat_history_prompt: list[tuple[str, str]],
) -> str:
    """분석된 질문으로부터 SQL 쿼리를 생성
    Returns:
        str: 생성된 SQL 쿼리문
    Raises:
        ValueError: SQL 쿼리를 생성할 수 없거나, 추출 패턴이 매치되지 않는 경우
        TypeError: LLM 응답이 예상된 형식이 아닌 경우.
    """
    try:
        today = datetime.now()
        prompt_today = today.strftime("%Y년 %m월 %d일")
        logger.info(f"nl2sql prompt_today: {prompt_today}")
        system_prompt = PROMPT_NL2SQL.format(today=prompt_today, main_com=company_id)

        few_shots = await retriever.get_few_shots(
            query_text=user_question, collection_name="shots_nl2sql", top_k=3
        )
        few_shot_prompt = []
        for example in reversed(few_shots):
            if "date" in example:
                human_with_date = f'{example["input"]}, 오늘: {example["date"]}.'
            else:
                human_with_date = example["input"]
            few_shot_prompt.append(("human", human_with_date))
            few_shot_prompt.append(("ai", example["output"]))

        # 시스템 메시지와 퓨샷 합치기
        flattend_few_shot_prompt = "\n".join(
            f"{role}: {text}" for role, text in few_shot_prompt
        )
        concat_few_shot_prompt = f"{system_prompt}\n{flattend_few_shot_prompt}"

        # 사용자의 질문 포맷팅
        formatted_today = today.strftime("%Y%m%d")
        weekday = WEEKDAYS[today.weekday()]

        formatted_question = f"{user_question}, 오늘: {formatted_today} {weekday}요일."

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=concat_few_shot_prompt),
                *chat_history_prompt,
                ("human", formatted_question),
            ]
        )

        logger.debug("===== nl2sql(Q) =====")
        qna_id = qna_manager.create_question(
            trace_id=trace_id, question=prompt, model="qwen_nl2sql"
        )

        chain = prompt | nl2sql
        output = chain.invoke(
            {"user_question": formatted_question, "main_com": company_id}
        )

        # 출력에서 SQL 쿼리 추출
        match = re.search(r"```sql\s*(.*?)\s*```", output, re.DOTALL)
        if match:
            sql_query = match.group(1)
        else:
            match = re.search(r"SELECT.*", output, re.DOTALL)
            if match:
                sql_query = match.group(0)

            else:
                logger.error("SQL query not found in output")
                raise ValueError("SQL 쿼리를 찾을 수 없습니다.")

        logger.debug("===== nl2sql(A) =====")
        logger.info(f"Generated SQL query: {sql_query}")
        qna_manager.record_answer(qna_id, output)

        return sql_query.strip()

    except Exception as e:
        logger.error(f"Error in create_sql: {str(e)}")
        raise
