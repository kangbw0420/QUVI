import pytest
import pandas as pd
from utils.table.expression_eval import SafeExpressionEvaluator

@pytest.fixture
def sample_data():
    """테스트를 위한 예시 데이터 생성"""
    # 수시입출계좌 데이터
    checking_data = {
        'acct_no': ['C001', 'C002', 'C003'],
        'acct_bal_amt': [1000000, 2000000, 3000000],
        'real_amt': [800000, 1800000, 2500000],
        'bank_nm': ['국민은행', '신한은행', '우리은행']
    }
    
    # 예적금 계좌 데이터
    savings_data = {
        'acct_no': ['S001', 'S002', 'S003', 'S004'],
        'acct_bal_amt': [5000000, 3000000, 7000000, 4000000],
        'curr_cd': ['KRW', 'KRW', 'KRW', 'KRW']
    }
    
    # 외화 예적금 계좌 데이터
    foreign_savings_data = {
        'acct_no': ['FS001', 'FS002', 'FS003', 'FS004', 'FS005'],
        'acct_bal_amt': [10000, 20000, 30000, 40000, 50000],
        'curr_cd': ['USD', 'JPY', 'EUR', 'GBP', 'USD']
    }
    
    # 대출 계좌 데이터
    loan_data = {
        'acct_no': ['L001', 'L002'],
        'acct_bal_amt': [10000000, 20000000],
        'loan_trsc_amt': [1000000, 2000000],
        'loan_intr_amt': [100000, 200000],
        'NOK_loan_trsc_amt': [10000, 20000],
        'PHP_loan_trsc_amt': [50000, 60000],
        'NOK_loan_intr_amt': [1000, 2000],
        'PHP_loan_intr_amt': [5000, 6000]
    }
    
    # 증권계좌 데이터
    stock_data = {
        'acct_no': ['ST001', 'ST002'],
        'deposit_amt': [5000000, 3000000],
        'total_appr_amt': [6000000, 3500000],
        'trsc_amt': [1000000, 500000]
    }
    
    # 거래내역 데이터
    transaction_data = {
        'in_out_dv': ['입금', '출금', '입금', '출금', '입금'],
        'trsc_amt': [1000000, 500000, 2000000, 1000000, 3000000],
        'note1': ['입금', '출금', '입금', '출금', '입금'],
        'curr_cd': ['USD', 'EUR', 'GBP', 'JPY', 'USD'],
        'trsc_month': ['202501', '202412', '202501', '202412', '202501'],
        'total_outgoing_amount': [500000, 600000, 700000, 800000, 900000],
        'NZD_deposit_amt': [1000, 2000, 3000, 4000, 5000],
        'NZD_withdrawal_amt': [500, 1000, 1500, 2000, 2500],
        'AED_deposit_amt': [2000, 4000, 6000, 8000, 10000],
        'AED_withdrawal_amt': [1000, 2000, 3000, 4000, 5000]
    }
    
    return {
        'checking': pd.DataFrame(checking_data),
        'savings': pd.DataFrame(savings_data),
        'foreign_savings': pd.DataFrame(foreign_savings_data),
        'loan': pd.DataFrame(loan_data),
        'stock': pd.DataFrame(stock_data),
        'transaction': pd.DataFrame(transaction_data)
    }

def test_checking_account_formatting(sample_data):
    """수시입출계좌 포맷팅 테스트"""
    evaluator = SafeExpressionEvaluator(sample_data['checking'])
    result = evaluator.eval_expression("f'현재 수시입출계좌 {df[\"acct_bal_amt\"].count()}개의 잔액은 {df[\"acct_bal_amt\"].sum()}원이며, 출금가능한 잔액은 {df[\"real_amt\"].sum()}원입니다.'")
    expected = "현재 수시입출계좌 3개의 잔액은 6,000,000원이며, 출금가능한 잔액은 5,100,000원입니다."
    assert result == expected

def test_savings_account_formatting(sample_data):
    """예적금 계좌 포맷팅 테스트"""
    evaluator = SafeExpressionEvaluator(sample_data['savings'])
    result = evaluator.eval_expression("f'현재 예적금 계좌는 총 {df[\"acct_no\"].count()}개이며, 잔액은 {df[\"acct_bal_amt\"].sum()}원입니다.'")
    expected = "현재 예적금 계좌는 총 4개이며, 잔액은 19,000,000원입니다."
    assert result == expected

def test_foreign_savings_account_formatting(sample_data):
    """외화 예적금 계좌 포맷팅 테스트"""
    evaluator = SafeExpressionEvaluator(sample_data['foreign_savings'])
    result = evaluator.eval_expression("f'현재 외화 예적금 계좌는 총 {df[\"acct_no\"].count()}개이며, 통화별로는 USD {len(df[df[\"curr_cd\"]==\"USD\"])}개, JPY {len(df[df[\"curr_cd\"]==\"JPY\"])}개, EUR {len(df[df[\"curr_cd\"]==\"EUR\"])}개, GBP {len(df[df[\"curr_cd\"]==\"GBP\"])}개 계좌가 있습니다.'")
    expected = "현재 외화 예적금 계좌는 총 5개이며, 통화별로는 USD 2개, JPY 1개, EUR 1개, GBP 1개 계좌가 있습니다."
    assert result == expected

def test_loan_account_formatting(sample_data):
    """대출 계좌 포맷팅 테스트"""
    evaluator = SafeExpressionEvaluator(sample_data['loan'])
    result = evaluator.eval_expression("f'현재 대출 계좌는 총 {df[\"acct_bal_amt\"].count()}개이며, 총 대출금액은 {df[\"acct_bal_amt\"].sum()}원입니다.'")
    expected = "현재 대출 계좌는 총 2개이며, 총 대출금액은 30,000,000원입니다."
    assert result == expected

def test_stock_account_formatting(sample_data):
    """증권계좌 포맷팅 테스트"""
    evaluator = SafeExpressionEvaluator(sample_data['stock'])
    result = evaluator.eval_expression("f'현재 증권계좌 총 {df[\"acct_no\"].count()}개의 예수금은 {df[\"deposit_amt\"].sum()}원이며, 평가금액은 {df[\"total_appr_amt\"].sum()}원입니다.'")
    expected = "현재 증권계좌 총 2개의 예수금은 8,000,000원이며, 평가금액은 9,500,000원입니다."
    assert result == expected

def test_transaction_formatting(sample_data):
    """거래내역 포맷팅 테스트"""
    evaluator = SafeExpressionEvaluator(sample_data['transaction'])
    result = evaluator.eval_expression("f'최근 한달 간 예적금 거래내역은 입금 총 {len(df[df[\"in_out_dv\"] == \"입금\"])}건 {df.loc[df[\"in_out_dv\"] == \"입금\", \"trsc_amt\"].sum():,}원, 출금 총 {len(df[df[\"in_out_dv\"] == \"출금\"])}건 {df.loc[df[\"in_out_dv\"] == \"출금\", \"trsc_amt\"].sum():,}원입니다.'")
    expected = "최근 한달 간 예적금 거래내역은 입금 총 3건 6,000,000원, 출금 총 2건 1,500,000원입니다."
    assert result == expected 