import unittest
from utils.fff import fulfill_fstring

class TestFulfillFString(unittest.TestCase):
    def setUp(self):
        # 테스트용 데이터 세팅
        self.result = [
            {
                "USD_acct_no": "111-111-111",
                "USD_acct_bal_amt": "1000.50",
                "JPY_acct_no": "222-222-222",
                "JPY_acct_bal_amt": "2000.75",
                "EUR_acct_no": "333-333-333",
                "EUR_acct_bal_amt": "3000.25",
                "KRW_acct_bal_amt": "5000",
                "intr_rate": "3.5",
                "bank_nm": "Test Bank"
            },
            {
                "USD_acct_no": "444-444-444",
                "USD_acct_bal_amt": "1500.50",
                "JPY_acct_no": "555-555-555",
                "JPY_acct_bal_amt": "2500.75",
                "EUR_acct_bal_amt": "3500.25",
                "KRW_acct_bal_amt": "5500",
                "intr_rate": "4.5",
                "bank_nm": "Another Bank"
            }
        ]
        
        self.column_list = [
            "USD_acct_no", "USD_acct_bal_amt",
            "JPY_acct_no", "JPY_acct_bal_amt",
            "EUR_acct_no", "EUR_acct_bal_amt",
            "KRW_acct_bal_amt", "intr_rate", "bank_nm"
        ]

    def test_simple_count(self):
        """단순 count 함수 테스트"""
        template = "계좌 개수: {count(USD_acct_no)}"
        expected = "계좌 개수: 2"
        self.assertEqual(fulfill_fstring(template, self.result, self.column_list), expected)

    def test_sum_with_decimal(self):
        """소수점이 있는 sum 테스트"""
        template = "USD 잔액 합계: {sum(USD_acct_bal_amt)}"
        expected = "USD 잔액 합계: 2,501.00"
        self.assertEqual(fulfill_fstring(template, self.result, self.column_list), expected)

    def test_count_addition(self):
        """count 함수들의 덧셈 테스트"""
        template = "전체 계좌 수: {count(USD_acct_no)+count(JPY_acct_no)}"
        expected = "전체 계좌 수: 4"
        self.assertEqual(fulfill_fstring(template, self.result, self.column_list), expected)

    def test_multiple_operations(self):
        """여러 연산자를 포함한 수식 테스트"""
        template = "계산 결과: {count(USD_acct_no)*2+count(JPY_acct_no)}"
        expected = "계산 결과: 6"
        self.assertEqual(fulfill_fstring(template, self.result, self.column_list), expected)

    def test_mixed_functions(self):
        """다른 종류의 함수가 포함된 복합 문자열 테스트"""
        template = "계좌 정보:\n계좌 수: {count(USD_acct_no)+count(JPY_acct_no)}\n은행: {unique(bank_nm)}"
        expected = "계좌 정보:\n계좌 수: 4\n은행: Another Bank, Test Bank"
        self.assertEqual(fulfill_fstring(template, self.result, self.column_list), expected)

    def test_krw_formatting(self):
        """KRW 금액 포맷팅 테스트"""
        template = "원화 잔액: {sum(KRW_acct_bal_amt)}"
        expected = "원화 잔액: 10,500"
        self.assertEqual(fulfill_fstring(template, self.result, self.column_list), expected)

    def test_interest_rate_decimal(self):
        """이자율 소수점 포맷팅 테스트"""
        template = "평균 이자율: {average(intr_rate)}"
        expected = "평균 이자율: 4.00"
        self.assertEqual(fulfill_fstring(template, self.result, self.column_list), expected)

    def test_multiple_currency_sums(self):
        """여러 통화의 합계를 포함한 복합 문자열 테스트"""
        template = """외화 잔액:
USD: {sum(USD_acct_bal_amt)}
JPY: {sum(JPY_acct_bal_amt)}
EUR: {sum(EUR_acct_bal_amt)}"""
        expected = """외화 잔액:
USD: 2,501.00
JPY: 4,501.50
EUR: 6,500.50"""
        self.assertEqual(fulfill_fstring(template, self.result, self.column_list), expected)

    def test_invalid_column(self):
        """존재하지 않는 컬럼 테스트"""
        template = "{sum(nonexistent_column)}"
        with self.assertRaises(ValueError):
            fulfill_fstring(template, self.result, self.column_list)

    def test_complex_arithmetic(self):
        """복잡한 산술 연산 테스트"""
        template = "복합 계산: {count(USD_acct_no)*3+count(JPY_acct_no)*2+count(EUR_acct_no)}"
        expected = "복합 계산: 9"
        self.assertEqual(fulfill_fstring(template, self.result, self.column_list), expected)

if __name__ == '__main__':
    unittest.main()