import pytest
import pandas as pd
from decimal import Decimal
import os
import sys
from typing import List, Dict, Any

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.table.calc_table import eval_fstring_template, SafeExpressionEvaluator


class TestFStringEvaluation:
    """Test class for evaluating f-string templates with dataframe operations."""
    
    @pytest.fixture
    def sample_banking_df(self) -> List[Dict[str, Any]]:
        """Generate sample banking data for testing."""
        return [
            {
                'bank_nm': '국민은행', 
                'acct_no': '123456789', 
                'acct_bal_amt': 1000000,
                'withdrawal_amt': 50000,
                'deposit_amt': 100000,
                'note1': '식비',
                'acct_cnt': 2,
                'curr_cd': 'KRW',
                'reg_dt': '20250101'
            },
            {
                'bank_nm': '국민은행',
                'acct_no': '234567890',
                'acct_bal_amt': 2000000,
                'withdrawal_amt': 30000,
                'deposit_amt': 200000,
                'note1': '교통비',
                'acct_cnt': 1,
                'curr_cd': 'KRW',
                'reg_dt': '20250102'
            },
            {
                'bank_nm': '신한은행',
                'acct_no': '345678901',
                'acct_bal_amt': 3000000,
                'withdrawal_amt': 40000,
                'deposit_amt': 300000,
                'note1': '식비',
                'acct_cnt': 3,
                'curr_cd': 'USD',
                'reg_dt': '20250103'
            },
            {
                'bank_nm': '우리은행',
                'acct_no': '456789012',
                'acct_bal_amt': 4000000,
                'withdrawal_amt': 60000,
                'deposit_amt': 400000,
                'note1': '여가비',
                'acct_cnt': 2,
                'curr_cd': 'KRW',
                'reg_dt': '20250104'
            }
        ]

    @pytest.fixture
    def decimal_df(self) -> List[Dict[str, Any]]:
        """Generate data with Decimal values for testing."""
        return [
            {'bank_nm': '국민은행', 'acct_bal_amt': Decimal('1000000.50'), 'intr_rate': Decimal('0.023')},
            {'bank_nm': '신한은행', 'acct_bal_amt': Decimal('2500000.75'), 'intr_rate': Decimal('0.025')},
            {'bank_nm': '우리은행', 'acct_bal_amt': Decimal('3000000.25'), 'intr_rate': Decimal('0.022')}
        ]

    def test_basic_aggregation(self, sample_banking_df):
        """Test basic aggregation functions."""
        # Sum of all acct_bal_amt values
        fstring = "총 계좌 잔액은 {sum(acct_bal_amt)}원입니다."
        result = eval_fstring_template(fstring, sample_banking_df)
        assert result == "총 계좌 잔액은 10000000원입니다."
        
        # Count of accounts
        fstring = "총 계좌 수는 {count(acct_no)}개입니다."
        result = eval_fstring_template(fstring, sample_banking_df)
        assert result == "총 계좌 수는 4개입니다."

    def test_filtering_operations(self, sample_banking_df):
        """Test filtering operations on dataframes."""
        # Using list comprehension to count specific bank entries
        fstring = "국민은행 계좌 수는 {len([row for row in df if row['bank_nm']=='국민은행'])}개입니다."
        result = eval_fstring_template(fstring, sample_banking_df)
        assert result == "국민은행 계좌 수는 2개입니다."
        
        # Get sum of specific bank's balance
        fstring = "국민은행 총 잔액은 {sum([row['acct_bal_amt'] for row in df if row['bank_nm']=='국민은행'])}원입니다."
        result = eval_fstring_template(fstring, sample_banking_df)
        assert result == "국민은행 총 잔액은 3000000원입니다."

    def test_list_operations(self, sample_banking_df):
        """Test operations that return lists."""
        # Get unique bank names using list comprehension
        fstring = "은행 목록: {list(set([row['bank_nm'] for row in df]))}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "국민은행" in result
        assert "신한은행" in result
        assert "우리은행" in result
        
        # List of note categories
        fstring = "적요 목록: {', '.join(set([row['note1'] for row in df]))}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "식비" in result
        assert "교통비" in result
        assert "여가비" in result

    def test_date_operations(self, sample_banking_df):
        """Test operations on date fields."""
        # Min and max dates
        fstring = "조회 기간: {min([row['reg_dt'] for row in df])}부터 {max([row['reg_dt'] for row in df])}까지"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "20250101부터 20250104까지" in result
        
        # Count items after a specific date
        fstring = "1월 2일 이후 계좌 수: {len([row for row in df if row['reg_dt'] > '20250102'])}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "1월 2일 이후 계좌 수: 2" in result

    def test_currency_filtering(self, sample_banking_df):
        """Test filtering by currency."""
        # Filter by KRW
        fstring = "원화 계좌 수: {len([row for row in df if row['curr_cd'] == 'KRW'])}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "원화 계좌 수: 3" in result
        
        # Filter by USD
        fstring = "달러 계좌 수: {len([row for row in df if row['curr_cd'] == 'USD'])}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "달러 계좌 수: 1" in result

    def test_formatting_values(self, sample_banking_df):
        """Test formatting of values in fstrings."""
        # Format with precision
        fstring = "평균 잔액: {average(acct_bal_amt):.2f}원"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "평균 잔액: 2500000.00원" in result
        
        # Format sum with custom format
        fstring = "총 출금액: {sum(withdrawal_amt)}원"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "총 출금액: 180000원" in result

    def test_decimal_handling(self, decimal_df):
        """Test handling of Decimal values."""
        # Sum of decimal values
        fstring = "총 잔액: {sum(acct_bal_amt)}"
        result = eval_fstring_template(fstring, decimal_df)
        assert "총 잔액: 6500001.5" in result or "총 잔액: 6500001.50" in result
        
        # Average interest rate
        fstring = "평균 이자율: {average(intr_rate):.4f}"
        result = eval_fstring_template(fstring, decimal_df)
        assert "평균 이자율: 0.0233" in result

    def test_complex_calculations(self, sample_banking_df):
        """Test more complex calculations involving multiple operations."""
        # Calculate ratio of withdrawal to deposit
        fstring = "출금/입금 비율: {sum(withdrawal_amt) / sum(deposit_amt):.2f}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "출금/입금 비율: 0.18" in result
        
        # Calculate average balance for accounts with withdrawal > 40000
        fstring = "출금액 4만원 초과 계좌 평균 잔액: {sum([row['acct_bal_amt'] for row in df if row['withdrawal_amt'] > 40000])/len([row for row in df if row['withdrawal_amt'] > 40000]):.0f}원"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "출금액 4만원 초과 계좌 평균 잔액: 2500000원" in result

    def test_custom_function_aliases(self, sample_banking_df):
        """Test custom function aliases defined in SafeExpressionEvaluator."""
        # count function
        fstring = "계좌 개수: {count(acct_no)}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "계좌 개수: 4" in result
        
        # average function
        fstring = "평균 잔액: {average(acct_bal_amt):.0f}원"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "평균 잔액: 2500000원" in result
        
        # list function
        fstring = "적요 목록: {list(note1)}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "식비" in result and "교통비" in result and "여가비" in result

    def test_security_file_access_prevention(self, sample_banking_df):
        """Test that file access attempts are prevented."""
        # Attempt to read a file
        fstring = "파일 내용: {open('/etc/passwd', 'r').read()}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "오류" in result or "Error" in result
        
        # Attempt to use os module
        fstring = "디렉토리 목록: {__import__('os').listdir('/')}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "오류" in result or "Error" in result

    def test_security_code_execution_prevention(self, sample_banking_df):
        """Test that code execution attempts are prevented."""
        # Attempt to execute system commands
        fstring = "명령 실행: {__import__('subprocess').check_output(['ls', '-la'])}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "오류" in result or "Error" in result
        
        # Attempt to use eval
        fstring = "악의적인 코드: {eval('__import__(\"os\").system(\"echo hacked\")')}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "오류" in result or "Error" in result

    def test_security_attribute_access_restriction(self, sample_banking_df):
        """Test that accessing disallowed attributes is prevented."""
        # Attempt to access __dict__
        fstring = "속성 접근: {df.__dict__}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "오류" in result or "Error" in result
        
        # Attempt to access __class__
        fstring = "클래스 접근: {df.__class__.__name__}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "오류" in result or "Error" in result

    def test_pandas_allowed_operations(self, sample_banking_df):
        """Test that basic pandas operations work correctly."""
        # Test safe operations
        fstring = "허용된 계산: {sum([row['acct_bal_amt'] for row in df])}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "오류" not in result and "Error" not in result
        assert "10000000" in result
        
        # Test unsafe operations (to_csv would be dangerous)
        fstring = "위험한 메서드: {df.to_csv('/tmp/output.csv')}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "오류" in result or "Error" in result

    def test_conditional_operations(self, sample_banking_df):
        """Test conditional operations in expressions."""
        # If-else expression with simple calculation
        fstring = "평균 잔액이 높은가요? {'높음' if average(acct_bal_amt) > 2000000 else '낮음'}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "평균 잔액이 높은가요? 높음" in result
        
        # Conditional using list comprehension
        fstring = "국민은행 계좌가 있나요? {'있음' if len([row for row in df if row['bank_nm'] == '국민은행']) > 0 else '없음'}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "국민은행 계좌가 있나요? 있음" in result

    def test_nested_functions(self, sample_banking_df):
        """Test nested function calls with list comprehensions."""
        # Find the bank with the maximum balance using list comprehension
        fstring = "최대 잔액 계좌 은행: {[row['bank_nm'] for row in df if row['acct_bal_amt'] == max([r['acct_bal_amt'] for r in df])][0]}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "최대 잔액 계좌 은행: 우리은행" in result
        
        # Find minimum deposit amount for a specific bank
        fstring = "국민은행의 최소 입금액: {min([row['deposit_amt'] for row in df if row['bank_nm'] == '국민은행'])}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "국민은행의 최소 입금액: 100000" in result

    def test_error_handling(self, sample_banking_df):
        """Test error handling in template evaluation."""
        # Non-existent column
        fstring = "존재하지 않는 컬럼: {sum([row.get('non_existent_column', 0) for row in df])}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert result == "존재하지 않는 컬럼: 0"  # Should handle gracefully
        
        # Division by zero should show error
        fstring = "0으로 나누기: {sum(acct_bal_amt) / (sum(withdrawal_amt) - sum(withdrawal_amt))}"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "오류" in result or "Error" in result or "inf" in result
        
        # Invalid syntax (missing closing brace)
        fstring = "잘못된 구문: {sum(acct_bal_amt"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert "오류" in result or "Error" in result

    def test_f_string_marker_removal(self, sample_banking_df):
        """Test that f-string markers are properly removed."""
        # f-string with double quotes
        fstring = 'f"총 계좌 수: {count(acct_no)}개"'
        result = eval_fstring_template(fstring, sample_banking_df)
        assert result == "총 계좌 수: 4개"
        
        # f-string with single quotes
        fstring = "f'총 계좌 수: {count(acct_no)}개'"
        result = eval_fstring_template(fstring, sample_banking_df)
        assert result == "총 계좌 수: 4개"