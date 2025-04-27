import pytest
import pandas as pd
from utils.table.compute_fstring import compute_fstring

@pytest.fixture
def sample_data():
    """테스트용 샘플 데이터를 생성합니다."""
    return pd.DataFrame({
        'acct_no': ['A001', 'A002', 'A003', 'A004'],
        'curr_cd': ['KRW', 'USD', 'JPY', 'KRW'],
        'acct_bal_amt': [1000000, 1000, 100000, 2000000],
        'view_dv': ['수시', '예적금', '대출', '외화']
    })

def test_basic_fstring(sample_data):
    """기본적인 f-string 포맷팅 테스트"""
    template = "총 계좌 수는 {df['acct_no'].count()}개입니다."
    result = compute_fstring(template, sample_data)
    assert result == "총 계좌 수는 4개입니다."

def test_number_formatting(sample_data):
    """숫자 포맷팅 테스트"""
    template = "KRW 계좌 잔액은 {df.loc[df['curr_cd'] == 'KRW', 'acct_bal_amt'].sum():,.0f}원입니다."
    result = compute_fstring(template, sample_data)
    assert result == "KRW 계좌 잔액은 3,000,000원입니다."

def test_list_comprehension(sample_data):
    """리스트 컴프리헨션을 사용한 f-string 테스트"""
    template = "각 통화별 잔액:\n{'\n'.join([f'- {curr}: {df.loc[df['curr_cd']==curr, 'acct_bal_amt'].sum():,.2f}' for curr in df['curr_cd'].unique()])}"
    result = compute_fstring(template, sample_data)
    expected = """각 통화별 잔액:
- KRW: 3,000,000.00
- USD: 1,000.00
- JPY: 100,000.00"""
    assert result == expected

def test_complex_expression(sample_data):
    """복잡한 표현식 테스트"""
    template = "수시 계좌의 평균 잔액은 {df.loc[df['view_dv'] == '수시', 'acct_bal_amt'].mean():,.0f}원입니다."
    result = compute_fstring(template, sample_data)
    assert result == "수시 계좌의 평균 잔액은 1,000,000원입니다."

def test_multiple_conditions(sample_data):
    """다중 조건을 사용한 테스트"""
    template = "KRW 수시 계좌의 잔액은 {df.loc[(df['curr_cd'] == 'KRW') & (df['view_dv'] == '수시'), 'acct_bal_amt'].sum():,.0f}원입니다."
    result = compute_fstring(template, sample_data)
    assert result == "KRW 수시 계좌의 잔액은 1,000,000원입니다."

def test_empty_dataframe():
    """빈 DataFrame 테스트"""
    empty_df = pd.DataFrame(columns=['acct_no', 'curr_cd', 'acct_bal_amt', 'view_dv'])
    template = "총 계좌 수는 {df['acct_no'].count()}개입니다."
    result = compute_fstring(template, empty_df)
    assert result == "총 계좌 수는 0개입니다."

def test_nested_fstring(sample_data):
    """중첩된 f-string 테스트"""
    template = "계좌 정보:\n{'\n'.join([f'계좌번호: {row.acct_no}, 잔액: {row.acct_bal_amt:,.0f}원' for _, row in df.iterrows()])}"
    result = compute_fstring(template, sample_data)
    expected = """계좌 정보:
계좌번호: A001, 잔액: 1,000,000원
계좌번호: A002, 잔액: 1,000원
계좌번호: A003, 잔액: 100,000원
계좌번호: A004, 잔액: 2,000,000원"""
    assert result == expected

def test_original_case(sample_data):
    """원래 문제가 되었던 케이스 테스트"""
    template = "현재 수시, 예적금, 대출, 외화 계좌 {df['acct_no'].count()}개의 잔액은  {'\n'.join([f'- {curr} {df.loc[df['curr_cd']==curr, 'acct_bal_amt'].sum():,.2f}' for curr in df['curr_cd'].unique()])} 입니다."
    result = compute_fstring(template, sample_data)
    expected = """현재 수시, 예적금, 대출, 외화 계좌 4개의 잔액은  
- KRW 3,000,000.00
- USD 1,000.00
- JPY 100,000.00 입니다."""
    assert result == expected 