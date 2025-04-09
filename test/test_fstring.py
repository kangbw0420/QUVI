import pytest
import pandas as pd
from utils.table.calc_table import evaluate_fstring_template


class TestFStringEvaluation:
    """테스트 클래스: f-string 형태의 응답 템플릿 계산 테스트"""
    
    @pytest.fixture
    def sample_df(self):
        """테스트용 샘플 데이터 생성"""
        data = [
            {
                'bank_nm': '국민은행', 
                'acct_no': '123456789', 
                'acct_bal_amt': 1000000,
                'withdrawal_amt': 50000,
                'deposit_amt': 100000,
                'note1': '식비'
            },
            {
                'bank_nm': '국민은행',
                'acct_no': '234567890',
                'acct_bal_amt': 2000000,
                'withdrawal_amt': 30000,
                'deposit_amt': 200000,
                'note1': '교통비'
            },
            {
                'bank_nm': '신한은행',
                'acct_no': '345678901',
                'acct_bal_amt': 3000000,
                'withdrawal_amt': 40000,
                'deposit_amt': 300000,
                'note1': '식비'
            },
            {
                'bank_nm': '우리은행',
                'acct_no': '456789012',
                'acct_bal_amt': 4000000,
                'withdrawal_amt': 60000,
                'deposit_amt': 400000,
                'note1': '여가비'
            }
        ]
        return data
    
    @pytest.fixture
    def sample_df_with_acct_cnt(self):
        """계좌 수를 포함한 테스트용 샘플 데이터 생성"""
        data = [
            {'bank_nm': '국민은행', 'acct_cnt': 2},
            {'bank_nm': '신한은행', 'acct_cnt': 1},
            {'bank_nm': '우리은행', 'acct_cnt': 1}
        ]
        return data
    
    def test_count_accounts_by_bank(self, sample_df_with_acct_cnt):
        """특정 은행 계좌 수 계산 테스트"""
        fstring = "현재 국민은행 수시입출계좌 수는 {df[df['bank_nm']=='국민은행']['acct_cnt'].tolist()[0]}개입니다."
        result = evaluate_fstring_template(fstring, sample_df_with_acct_cnt)
        assert result == "현재 국민은행 수시입출계좌 수는 2개입니다."
    
    def test_sum_accounts(self, sample_df_with_acct_cnt):
        """총 계좌 수 합계 계산 테스트"""
        fstring = "현재 수시입출계좌 수는 {df['acct_cnt'].sum()}개입니다."
        result = evaluate_fstring_template(fstring, sample_df_with_acct_cnt)
        assert result == "현재 수시입출계좌 수는 4개입니다."
    
    def test_loan_account_summary(self, sample_df):
        """대출 계좌 수 및 총 대출금액 계산 테스트"""
        fstring = "현재 대출 계좌는 총 {len(df['acct_no'])}개이며, 총 대출금액은 {df['acct_bal_amt'].sum()}원입니다."
        result = evaluate_fstring_template(fstring, sample_df)
        assert result == "현재 대출 계좌는 총 4개이며, 총 대출금액은 10000000원입니다."
    
    def test_category_withdrawal_summary(self, sample_df):
        """특정 카테고리별 지출 건수 및 금액 계산 테스트"""
        # 식비 지출 필터링
        food_expenses = [row for row in sample_df if row['note1'] == '식비']
        
        fstring = "최근 한달간 식비에 나간 돈은 총 {len(df[df['note1']=='식비'])}건 {df[df['note1']=='식비']['withdrawal_amt'].sum()}원입니다."
        result = evaluate_fstring_template(fstring, sample_df)
        assert result == "최근 한달간 식비에 나간 돈은 총 2건 90000원입니다."
    
    def test_multiple_notes_list(self, sample_df):
        """여러 노트(카테고리) 목록 표시 테스트"""
        fstring = "최근 한달간 거래 내역의 카테고리는 {df['note1'].unique().tolist()}입니다."
        result = evaluate_fstring_template(fstring, sample_df)
        assert "식비" in result
        assert "교통비" in result
        assert "여가비" in result
    
    def test_total_withdrawal_amount(self, sample_df):
        """총 출금액 계산 테스트"""
        fstring = "최근 한달간 출금 총액은 {df['withdrawal_amt'].sum()}원입니다."
        result = evaluate_fstring_template(fstring, sample_df)
        assert result == "최근 한달간 출금 총액은 180000원입니다."
    
    def test_count_withdrawal_transactions(self, sample_df):
        """출금 거래 건수 계산 테스트"""
        fstring = "최근 한달간 출금 건수는 {df['withdrawal_amt'].count()}건입니다."
        result = evaluate_fstring_template(fstring, sample_df)
        assert result == "최근 한달간 출금 건수는 4건입니다."
    
    def test_average_deposit_amount(self, sample_df):
        """평균 입금액 계산 테스트"""
        fstring = "최근 한달간 평균 입금액은 {df['deposit_amt'].mean():.0f}원입니다."
        result = evaluate_fstring_template(fstring, sample_df)
        assert result == "최근 한달간 평균 입금액은 250000원입니다."
    
    def test_custom_expression_replacement(self, sample_df):
        """사용자 정의 표현식 치환 테스트 (count 함수 사용)"""
        fstring = "거래 건수는 {count(acct_no)}건입니다."
        result = evaluate_fstring_template(fstring, sample_df)
        assert result == "거래 건수는 4건입니다."
    
    def test_error_handling(self, sample_df):
        """오류 처리 테스트"""
        fstring = "잘못된 표현식: {df['non_existing_column'].sum()}"
        result = evaluate_fstring_template(fstring, sample_df)
        assert "Error" in result