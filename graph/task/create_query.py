import re
from typing import List
from datetime import datetime

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from database.database_service import DatabaseService
from graph.models import qwen_llm
from utils.retriever import retriever
from llm_admin.qna_manager import QnAManager

database_service = DatabaseService()
qna_manager = QnAManager()

WEEKDAYS = {
    0: '월',
    1: '화',
    2: '수',
    3: '목',
    4: '금',
    5: '토',
    6: '일'
}

async def create_query(
    trace_id: str, 
    selected_table: str, 
    user_question: str,
    main_com: str,
    sub_coms: List[str],
    today: str
) -> str:
    """분석된 질문으로부터 SQL 쿼리를 생성
    Returns:
        str: 생성된 SQL 쿼리문
    Raises:
        ValueError: SQL 쿼리를 생성할 수 없거나, 추출 패턴이 매치되지 않는 경우
        TypeError: LLM 응답이 예상된 형식이 아닌 경우.
    """
    try:
        sub_coms_quoted = [f"'{com}'" for com in sub_coms]
        sub_coms_list = ", ".join(sub_coms_quoted)
        
        # IN 절을 위한 모든 회사 리스트 (main_com + sub_coms)
        all_companies = [main_com] + sub_coms
        all_coms_quoted = [f"'{com}'" for com in all_companies]
        all_coms_list = ", ".join(all_coms_quoted)

        try:
            system_prompt = database_service.get_prompt(
                node_nm='create_query', 
                prompt_nm=selected_table
            )[0]['prompt'].format(
                today=today,
                main_com=main_com,
                sub_coms=sub_coms_list,
                all_coms=all_coms_list
            )

        except FileNotFoundError as e:
            system_prompt = database_service.get_prompt(node_nm='create_query', prompt_nm='system')[0]['prompt'].format(today=today)

        # 콜렉션 이름은 shots_trsc, shots_amt와 같이 구성됨
        collection_name = f"shots_{selected_table}"

        few_shots = await retriever.get_few_shots(
            query_text=user_question,
            collection_name=collection_name,
            top_k=3
        )
        few_shot_prompt = []
        for example in few_shots:
            if "date" in example:
                human_with_date = f'{example["input"]}, 오늘: {example["date"]}.'
            else:
                human_with_date = example["input"]
            few_shot_prompt.append(("human", human_with_date))
            few_shot_prompt.append(("ai", example["output"]))

        today_date = datetime.strptime(today, "%Y-%m-%d")
        formatted_today = today_date.strftime("%Y%m%d")
        weekday = WEEKDAYS[today_date.weekday()]

        formatted_question = f"{user_question}, 오늘: {formatted_today} {weekday}요일."

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_prompt),
                *few_shot_prompt,
                ("human", formatted_question),
            ]
        )

        print("=" * 40 + "nl2sql(Q)" + "=" * 40)
        qna_id = qna_manager.create_question(
            trace_id=trace_id,
            question=prompt,
            model="qwen_14b"
        )

        chain = prompt | qwen_llm
        output = chain.invoke(
            {"user_question": formatted_question}
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
                raise ValueError("SQL 쿼리를 찾을 수 없습니다.")
        
        print("=" * 40 + "nl2sql(A)" + "=" * 40)
        print(output)
        qna_manager.record_answer(qna_id, output)

        return sql_query.strip()

    except Exception as e:
        raise