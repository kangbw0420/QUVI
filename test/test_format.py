import unittest
from decimal import Decimal
from utils.compute.main_compute import compute_fstring
from utils.compute.formatter import format_number, should_use_decimals
from utils.compute.computer import compute_function, safe_decimal

class TestFormatNumber(unittest.TestCase):
    def setUp(self):
        print("\n=== Setting up test data ===")
        # Sample data setup
        self.result = [
            {
                'intr_rate': Decimal('3.45'),
                'acct_bal_amt': Decimal('10000000'),
            },
            {
                'intr_rate': Decimal('4.25'),
                'acct_bal_amt': Decimal('20000000'),
            },
            {
                'intr_rate': Decimal('3.85'),
                'acct_bal_amt': Decimal('15000000'),
            }
        ]
        self.column_list = ['intr_rate', 'acct_bal_amt']
        print(f"Test data initialized with {len(self.result)} records")
        print("Sample record:", self.result[0])
        print("Columns:", self.column_list)

    def test_decimal_formatting_in_complex_expression(self):
        """Test that decimal formatting works correctly in a complex weighted average expression"""
        print("\n=== Testing complex weighted average expression ===")
        fstring = "대출 가중 평균 이자율은 {sumproduct(intr_rate, acct_bal_amt)/sum(acct_bal_amt)}%입니다."
        print("Testing f-string:", fstring)

        # Test intermediate calculations
        print("\nTesting intermediate calculations:")
        numerator = compute_function('sumproduct', ['intr_rate', 'acct_bal_amt'], self.result, self.column_list)
        denominator = compute_function('sum', ['acct_bal_amt'], self.result, self.column_list)
        print(f"sumproduct(intr_rate, acct_bal_amt) = {numerator}")
        print(f"sum(acct_bal_amt) = {denominator}")
        print(f"Division type check - numerator: {type(numerator)}, denominator: {type(denominator)}")

        # Manual decimal calculation for verification
        total_weighted = sum(safe_decimal(row['intr_rate']) * safe_decimal(row['acct_bal_amt']) for row in self.result)
        total_balance = sum(safe_decimal(row['acct_bal_amt']) for row in self.result)
        expected_rate = total_weighted / total_balance
        print(f"\nManual calculation:")
        print(f"Total weighted sum: {total_weighted}")
        print(f"Total balance: {total_balance}")
        print(f"Expected rate before formatting: {expected_rate}")

        # Test decimal formatting
        print("\nTesting should_use_decimals for division result:")
        print(f"should_use_decimals('result', '', ['intr_rate']) = {should_use_decimals('result', '', ['intr_rate'])}")
        print(f"should_use_decimals('result', 'division', ['intr_rate', 'acct_bal_amt']) = {should_use_decimals('result', 'division', ['intr_rate', 'acct_bal_amt'])}")

        # Get actual result
        result = compute_fstring(fstring, self.result, self.column_list)
        print("\nFinal formatted result:", result)

        self.assertEqual(result, "대출 가중 평균 이자율은 3.94%입니다.")

if __name__ == '__main__':
    unittest.main(verbosity=2)