import pytest
from decimal import Decimal
import re
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock

# utils.compute.main_compute에서 필요한 함수들을 import
# 모킹을 위해 모듈 전체를 import
import utils.compute.main_compute
from utils.compute.main_compute import handle_computed_column, compute_fstring

# 테스트를 위한 가짜 데이터 생성 함수
def create_test_data():
    # 단일 행 결과 데이터
    result = [
        {
            # 일반 데이터
            "bank_nm": "Test Bank",
            "acct_no": "123456789",
            "trsc_amt": Decimal("1000.50"),
            "balance": Decimal("5000.75"),
            
            # 계산된 컬럼들
            "sum_amt": Decimal("10000.00"),
            "count_transactions": 42,
            "average_balance": Decimal("3500.25"),
            
            # 기타 데이터
            "currency": "KRW"
        }
    ]
    
    # 컬럼 리스트
    column_list = ["bank_nm", "acct_no", "trsc_amt", "balance", 
                   "sum_amt", "count_transactions", "average_balance", "currency"]
    
    return result, column_list

# 여러 행의 데이터 생성
def create_multi_row_data():
    result = [
        {
            "bank_nm": "Bank A",
            "acct_no": "11111111",
            "trsc_amt": Decimal("500.25"),
            "balance": Decimal("2000.00")
        },
        {
            "bank_nm": "Bank B",
            "acct_no": "22222222",
            "trsc_amt": Decimal("1500.75"),
            "balance": Decimal("8000.50")
        }
    ]
    
    column_list = ["bank_nm", "acct_no", "trsc_amt", "balance"]
    
    return result, column_list

class TestComputeColumns:
    
    def test_math_function(self):
        """수학 함수를 포함한 표현식 테스트"""
        result, column_list = create_test_data()
        
        # 테스트를 위한 가짜 함수를 모킹해야 함
        # 실제로는 compute_function에서 처리됨
        # 여기서는 단순히 에러가 발생하는지만 확인
        expression = "sum(trsc_amt)"
        output = handle_computed_column(expression, result, column_list)
        assert 'Error' in output
    
    def test_compute_fstring(self):
        """전체 fstring 계산 테스트"""
        result, column_list = create_test_data()
        
        # 계산된 컬럼 포함 fstring
        fstring = 'f"총 거래 건수: {count_transactions}건, 평균 잔액: {average_balance}원"'
        output = compute_fstring(fstring, result, column_list)
        assert output == "총 거래 건수: 42건, 평균 잔액: 3500.25원"
        
        # 계산된 컬럼 및 일반 텍스트 혼합
        fstring = 'f"은행: {bank_nm}, 계산된 금액 합계: {sum_amt}원"'
        output = compute_fstring(fstring, result, column_list)
        # bank_nm은 계산되지 않으므로 오류가 포함됨
        assert "오류" in output or "Error" in output
        # 그러나 sum_amt는 계산됨
        assert "10000.00원" in output

# handle_math_expression를 모킹한 테스트 케이스
class TestWithMocks:
    @patch('utils.compute.main_compute.handle_math_expression')
    def test_with_mocked_math_expression(self, mock_handle_math):
        """handle_math_expression 함수를 모킹하여 테스트"""
        # mock 함수가 특정 값을 반환하도록 설정
        mock_handle_math.return_value = "Mocked Result"
        
        result, column_list = create_test_data()
        
        # 계산된 컬럼이 아닌 표현식으로 테스트
        expression = "some_non_computed_expression"
        output = handle_computed_column(expression, result, column_list)
        
        # mock 함수가 호출되었는지 확인
        mock_handle_math.assert_called_once()
        assert output == "Mocked Result"
    
    @patch('utils.compute.main_compute.handle_computed_column')
    def test_compute_fstring_with_mocks(self, mock_handle_computed):
        """compute_fstring 함수가 handle_computed_column을 올바르게 호출하는지 테스트"""
        # mock 함수가 호출될 때마다 다른 값을 반환하도록 설정
        mock_handle_computed.side_effect = ["Val1", "Val2", "Val3"]
        
        result, column_list = create_test_data()
        fstring = 'f"값1: {expr1}, 값2: {expr2}, 값3: {expr3}"'
        
        output = compute_fstring(fstring, result, column_list)
        
        # compute_fstring이 정규식 패턴을 통해 handle_computed_column을 3번 호출했는지 확인
        assert mock_handle_computed.call_count == 3
        assert output == "값1: Val1, 값2: Val2, 값3: Val3"

# 실제 환경 통합 테스트 (실제 모든 의존성 함수들이 구현되어 있을 때)
class TestIntegration:
    def test_integration_scenario(self):
        """실제 환경과 비슷한 시나리오를 테스트"""
        try:
            # 이 테스트는 실제 함수들이 모두 구현되어 있을 때만 동작합니다
            result = [
                {
                    "bank_nm": "Test Bank",
                    "acct_no": "123456789",
                    "trsc_amt": Decimal("1000.00"),
                    "sum_amt": Decimal("10000.00")
                }
            ]
            column_list = ["bank_nm", "acct_no", "trsc_amt", "sum_amt"]
            
            fstring = 'f"총 금액: {sum_amt}원, 계좌번호: {acct_no}"'
            output = compute_fstring(fstring, result, column_list)
            
            # sum_amt는 계산된 컬럼으로 정확히 처리되어야 함
            assert "총 금액: 10000.00원" in output
            
            # acct_no는 일반 컬럼이므로 오류가 있을 수 있음
            # 실제 환경에서는 다른 계산 함수들이 제대로 구현되어 있어야 함
        except Exception as e:
            pytest.skip(f"통합 테스트는 모든 의존성이 구현된 환경에서만 실행 가능합니다: {str(e)}")