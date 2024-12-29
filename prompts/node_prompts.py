from prompts.prompt_retriever import shots_retriever
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate

def get_planner_prompt(task):
    base_prompt = """
    다음 Task에 답변하기 위한 단계별 계획을 수립하라.
    각 계획에 대한 결과를 도출하기 위해 사용할 외부 도구와 도구 입력값을 함께 표시하세요.
    결과는 나중에 도구가 호출할 수 있는 변수 #E에 저장할 수 있다. (PLAN, #E1, PLAN, #E2, PLAN, ...)
    계획을 자세히 설명하라. 각 계획 뒤에는 하나의 #E만 있어야 한다.

    주의사항:
    1. 우리 회사의 이름은 "웹케시"임. 그렇기에 "웹케시 수시입출계좌 거래내역"과 같은 질의는 "웹케시"를 생략하고 "수시입출계좌 거래내역"을 의미
    2. 날짜가 필요하면 현재 날짜인 {today} 기준으로 계산
    3. 시간 범위가 지정되지 않으면 기본값 1년
    4. 도구는 다음 중 하나로 한 번만 사용 가능

    <tool_list>
    (1) load_transaction_data[from_date,to_date]: API 호출로 금융 거래 데이터를 load. 언제부터 언제까지의 데이터를 검색할지 지정하세요. from_date와 to_date는 YYYYMMDD 형식이어야 합니다.
    (2) load_balance_data[]: 현재 금융 잔액 데이터를 로드합니다. 인수가 필요하지 않습니다.
    (3) transaction_sql[query, source]: LLM(NL2SQL)을 사용하여 금융 거래 관련 SQL을 생성하고, 생성된 쿼리로 transaction 테이블을 조회합니다. 입력 인수는 자연어입니다. 데이터를 어디서 가져올지 명시할 필요는 없습니다.
    (4) balance_sql[query, source]: LLM(NL2SQL)을 사용하여 금융 잔액 관련 SQL을 생성하고, 생성된 쿼리로 balance 테이블을 조회합니다. 입력 쿼리는 자연어입니다. 데이터를 어디서 가져올지 명시할 필요는 없습니다.
    (5) load_past_balance_data[date]: API 호출로 특정 시점의 과거 금융 잔액 데이터를 로드합니다. 조회하고자 하는 날짜를 YYYYMMDD 형식으로 지정하세요.
    (6) past_balance_sql[query, source]: LLM(NL2SQL)을 사용하여 과거 금융 잔액 관련 SQL을 생성하고, 생성된 쿼리로 past_balance 테이블을 조회합니다. 입력 쿼리는 자연어입니다. 데이터를 어디서 가져올지 명시할 필요는 없습니다.
    (7) load_loan_transaction_data[from_date,to_date]: API 호출로 대출 거래 데이터를 로드합니다. 언제부터 언제까지의 데이터를 검색할지 지정하세요. from_date와 to_date는 YYYYMMDD 형식이어야 합니다.
    (8) load_loan_balance_data[]: 현재 대출 잔액 데이터를 로드합니다. 인수가 필요하지 않습니다.
    (9) loan_transaction_sql[query, source]: LLM(NL2SQL)을 사용하여 대출 거래 관련 SQL을 생성하고, 생성된 쿼리로 loan_transaction 테이블을 조회합니다. 입력 인수는 자연어입니다. 데이터를 어디서 가져올지 명시할 필요는 없습니다.
    (10) loan_balance_sql[query, source]: LLM(NL2SQL)을 사용하여 대출 잔액 관련 SQL을 생성하고, 생성된 쿼리로 loan_balance 테이블을 조회합니다. 입력 쿼리는 자연어입니다. 데이터를 어디서 가져올지 명시할 필요는 없습니다.    
    (11) calculator[expression]: expression을 평가해서 계산합니다.
    (12) pass: 아무런 tool도 사용하지 않습니다.

    예시:
    {shots}
            
    Task: {task}"""

    today = datetime.now().strftime("%Y-%m-%d")

    shots = shots_retriever(task=task, node="planner")

    partial_prompt = base_prompt.format(today=today, shots=shots, task="{task}")

    prompt = ChatPromptTemplate.from_messages([("user", partial_prompt)])

    return prompt