from prompts.prompt_retriever import shots_retriever
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate

today = datetime.now().strftime("%Y-%m-%d")


def get_trsc_nl2sql_prompt(task):
    system_prompt = """
                너는 금융 관련 duckDB 전문가야.
                다음 table schema를 참고해서 사용자의 자연어 질문을 SQL문으로 바꿔.
                시간은 TRSC_DT를 사용해.
                답변에는 SQL 구문만 보여줘.
    """
    base_prompt = """
                오늘은 {today}야.

                Table: bank_transactions (은행 거래 내역)

                Columns:
                - TRSC_TM: 거래시각 (144934는 14시 49분 34초를 의미)
                - BANK_NM: 거래은행 (예: 신한은행, 국민은행 등)
                - TRSC_AMT: 거래금액 (원화 기준, 소수점 2자리까지)
                - TRSC_DT: 거래일자 (YYYY-MM-DD 형식)
                - ACCT_NO: 계좌번호 (숫자로 구성된 문자열)
                - TRSC_BAL: 거래 후 계좌잔액 (원화 기준, 소수점 2자리까지)
                - IN_OUT_DV: 입출금구분 (1=입금, 2=출금)
                - NOTE1: 거래메모 (거래 설명, 적요)

                예시:
                {shots}
                
                질문:{input}
                SQL:
    """

    shots = shots_retriever(task=task, node="trsc_nl2sql")

    partial_prompt = base_prompt.format(today=today, shots=shots, input="{input}")

    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("user", partial_prompt)]
    )

    return prompt


def get_balance_nl2sql_prompt(task):
    system_prompt = """
                당신은 금융 관련 duckDB 전문가입니다.
                다음 table schema를 참고해서 사용자의 자연어 질문을 SQL문으로 바꿔주세요.
                최대한 칼럼명은 바꾸지 마세요.

                Table: account_balances (계좌 잔액 정보)

                Columns:
                - REAL_AMT: 실제 금액 (원화 기준)
                - BANK_NM: 은행명
                - ACCT_BAL_AMT: 계좌 잔액
                - TRAN_DATE: 거래일자
                - ACCT_NO: 계좌번호
                - ACCT_DV_NM: 계좌구분명 (예: 정기예금, 외화계좌, 기업자유예금 등)

                예시:
                질문: "우리 은행 잔액은?"
                SQL: FROM account_balances WHERE BANK_NM = '우리은행';

                질문: "은행별 잔액은?"
                SQL: SELECT BANK_NM, SUM(REAL_AMT) AS REAL_AMT FROM account_balances GROUP BY BANK_NM;

                질문: "총 잔액 및 은행별 잔액을 계산해줘"
                SQL: SELECT COALESCE(BANK_NM, '총 잔액') as BANK_NM, SUM(REAL_AMT) AS BANK_REAL_AMT, COUNT(*) as COUNT FROM account_balances GROUP BY ROLLUP(BANK_NM);
                
                질문: "계좌번호가 6789로 끝나는 계좌의 잔액을 보여줘"
                SQL: FROM account_balances WHERE ACCT_NO LIKE '%6789';

                질문: "기업은행 계좌만 금액이 많은 순으로 정렬해줘",
                SQL: "SELECT * FROM account_balances WHERE BANK_NM = '기업은행' ORDER BY REAL_AMT DESC"

                질문: "농협은행 계좌만 보여줘",
                SQL: "SELECT * FROM account_balances WHERE BANK_NM = '농협'"

                질문: "수협은행의 잔액을 큰 순서대로 정렬해줘",
                SQL: "SELECT * FROM account_balances WHERE BANK_NM = '수협은행' ORDER BY REAL_AMT DESC"

                질문: "농협 잔액을 작은 순으로 정렬해줘"
                SQL: "SELECT * FROM account_balances WHERE BANK_NM = '농협' ORDER BY REAL_AMT ASC"

                질문: "우리은행 수시 입출 계좌 잔액 작은 순으로 조회",
                SQL: "SELECT * FROM account_balances WHERE BANK_NM = '우리은행' ORDER BY REAL_AMT ASC"
                
                결과값으로는 SQL 쿼리문만 생성해주세요.
    """
    base_prompt = """
                {input}
    """
    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("user", base_prompt)]
    )

    return prompt


def get_past_balance_nl2sql_prompt(task):
    system_prompt = """
                당신은 금융 관련 duckDB 전문가입니다.
                다음 table schema를 참고해서 사용자의 자연어 질문을 SQL문으로 바꿔주세요.
                최대한 칼럼명은 바꾸지 마세요.
                오늘은 {today}야.

                Table: account_balances_past (과거 계좌 잔액 정보)

                Columns:
                - BANK_NM: 은행명         
                - ACCT_NO: 계좌번호   
                - ACCT_BAL_AMT: 계좌잔액   
                - REG_DT: 일자 

                예시:
                질문: "우리 은행 잔액은?"
                SQL: FROM account_balances_past WHERE BANK_NM = '우리은행';

                질문: "은행별 잔액은?"
                SQL: SELECT BANK_NM, SUM(REAL_AMT) AS REAL_AMT FROM account_balances_past GROUP BY BANK_NM;
                
                결과값으로는 SQL 쿼리문만 생성해주세요.
    """.format(
        today=today
    )
    base_prompt = """
                {input}
    """
    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("user", base_prompt)]
    )

    return prompt


def get_loan_balance_nl2sql_prompt(task):
    system_prompt = """
                당신은 금융 관련 duckDB 전문가입니다.
                다음 table schema를 참고해서 사용자의 자연어 질문을 SQL문으로 바꿔주세요.
                최대한 칼럼명은 바꾸지 마세요.
                결과값으로는 SQL 쿼리문만 생성해주세요.
                오늘은 {today}야.
                
                Table: loan_accounts (대출 계좌 정보)
                
                Columns:
                - BANK_CD: 은행 코드
                - ACCT_NO: 계좌번호
                - ACCT_DV: 계좌구분
                - CURR_CD: 통화코드
                - ACCT_NICK_NM: 계좌 별칭
                - ACCT_BAL_AMT: 계좌 잔액
                - NEW_DT: 신규일자
                - DUE_DT: 만기일자
                - CNTRCT_AMT: 계약금액
                - INTR_RATE: 이자율
                - LOAN_SBJT: 대출 과목
                - REPAY_MTHD: 상환 방법
                - INTR_PAY_DT: 이자 납입일
                - TRMN_YN: 해지 여부
                - TRMN_DT: 해지 일자
                - OPEN_DT: 개설일자
                - REG_DTM: 등록일시
                - CORC_DTM: 수정일시

                예시:
                질문: "산업은행 대출 잔액은?"
                SQL: SELECT SUM(ACCT_BAL_AMT) FROM loan_accounts WHERE BANK_CD = '산업은행';

                질문: "은행별 대출 잔액은?"
                SQL: SELECT BANK_CD, SUM(ACCT_BAL_AMT) as TOTAL_AMOUNT FROM loan_accounts GROUP BY BANK_CD WHERE AND DUE_DT > '{today}';

                질문: "이자율이 3% 이상인 대출 계좌 조회"
                SQL: SELECT * FROM loan_accounts WHERE CAST(INTR_RATE AS FLOAT) >= 3.0;

                질문: "2024년에 만기되는 대출 계좌 조회"
                SQL: SELECT * FROM loan_accounts WHERE DUE_DT LIKE '2024%';

                질문: "은행별 가중 평균 금리를 계산해줘"
                SQL: SELECT BANK_CD, SUM(CAST(INTR_RATE AS FLOAT) * CNTRCT_AMT) / SUM(CNTRCT_AMT) as WEIGHTED_AVG_RATE, SUM(CNTRCT_AMT) as SUM_CNTRCT_AMT FROM loan_accounts WHERE CAST(INTR_RATE AS FLOAT) > 0 AND INTR_RATE IS NOT NULL AND DUE_DT > '{today}' GROUP BY BANK_CD;

                질문: "미상환 잔액이 있는 계좌만 조회"
                SQL: SELECT * FROM loan_accounts WHERE CAST(ACCT_BAL_AMT AS FLOAT) > 0;
                
                질문: "가중 평균 금리를 계산해줘"   
                SQL: SELECT SUM(CAST(LOAN_RATE AS FLOAT) * LOAN_TRSC_AMT) / SUM(LOAN_TRSC_AMT) as WEIGHTED_AVG_RATE, SUM(CNTRCT_AMT) as SUM_CNTRCT_AMT FROM loan_transactions WHERE CAST(LOAN_RATE AS FLOAT) > 0 AND LOAN_RATE IS NOT NULL AND DUE_DT > '{today}';
    """.format(
        today=today
    )
    base_prompt = """
                질문: {input}
    """
    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("user", base_prompt)]
    )

    return prompt


def get_loan_trsc_nl2sql_prompt(task):
    system_prompt = """
                loan_transactions 테이블에 대한 SQL 쿼리 생성 프롬프트를 만들어드리겠습니다:
                당신은 금융 관련 duckDB 전문가입니다.
                다음 table schema를 참고해서 사용자의 자연어 질문을 SQL문으로 바꿔주세요.
                duckDB 특수 sql 구문을 활용해주세요.
                최대한 칼럼명은 바꾸지 마세요.
                결과값으로는 SQL 쿼리문만 생성해주세요.
                
                Table: loan_transactions (대출 거래 내역)
                
                Columns:
                - BANK_CD: 은행 코드
                - ACCT_NO: 계좌번호
                - TRSC_DT: 거래일자
                - TRSC_SEQ_NO: 거래순번
                - CURR_CD: 통화코드
                - LOAN_TRSC_DV: 대출거래구분
                - TRSC_AMT: 거래금액
                - LOAN_TRSC_AMT: 대출거래금액
                - LOAN_BAL: 대출잔액
                - LOAN_RATE: 대출금리
                - LOAN_INTR_ST_DT: 대출이자시작일
                - LOAN_INTR_EN_DT: 대출이자종료일
                - LOAN_INTR_AMT: 대출이자금액
                - NOTE1: 비고1
                - MNUL_WRT_YN: 수동작성여부

                예시:
                질문: "계좌별 총 이자 납부금액은?"
                SQL: SELECT ACCT_NO, SUM(LOAN_INTR_AMT) as TOTAL_INTEREST FROM loan_transactions WHERE LOAN_TRSC_DV = '이자수입' GROUP BY ACCT_NO;

                질문: "기업은행 원금 상환 내역 조회"
                SQL: SELECT * FROM loan_transactions WHERE BANK_CD = '기업은행' AND LOAN_TRSC_DV = '원금상환' ORDER BY TRSC_DT DESC;
                
                질문: "11월 대출 거래내역 조회"
                SQL: SELECT * FROM loan_transactions WHERE TRSC_DT LIKE '202411%' ORDER BY TRSC_DT DESC;
                
                질문: "이자율이 5% 이상인 거래내역"
                SQL: SELECT * FROM loan_transactions WHERE CAST(LOAN_RATE AS FLOAT) >= 5.0;
                
                질문: "거래구분별 거래 건수"
                SQL: SELECT LOAN_TRSC_DV, COUNT(*) as COUNT FROM loan_transactions GROUP BY LOAN_TRSC_DV;

    """
    base_prompt = """
                질문: {input}
    """
    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("user", base_prompt)]
    )

    return prompt
