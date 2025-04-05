import pytest
from decimal import Decimal
from typing import List, Dict, Any

# 테스트할 모듈 임포트
from utils.table.format_table import format_table_pipe, format_table_html

# 테스트 데이터 설정을 위한 fixture
@pytest.fixture
def sample_data():
    return [
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

@pytest.fixture
def tuple_wrapped_data(sample_data):
    """튜플로 감싸진 데이터 샘플"""
    return (sample_data,)

@pytest.fixture
def nested_data():
    return [
        {
            "key": {"title": "Group 1"},
            "data": [
                {"col1": "value1", "col2": "value2"},
                {"col1": "value3", "col2": "value4"}
            ]
        },
        {
            "key": {"title": "Group 2"},
            "data": [
                {"col1": "value5", "col2": "value6"},
                {"col1": "value7", "col2": "value8"}
            ]
        }
    ]

@pytest.fixture
def large_data():
    """12개 행을 가진 데이터셋 생성"""
    return [
        {"id": i, "name": f"Item {i}", "value": Decimal(i * 100)} 
        for i in range(1, 13)
    ]

class TestUpdatedFormatTable:
    
    def test_format_table_pipe_basic(self, sample_data):
        """기본 파이프 테이블 포맷 테스트"""
        result = format_table_pipe(sample_data)
        
        # 헤더 확인
        assert "bank_nm | acct_no | trsc_amt | balance" in result
        
        # 데이터 행 확인
        assert "Bank A | 11111111 | 500.25 | 2000.00" in result
        assert "Bank B | 22222222 | 1500.75 | 8000.50" in result

    def test_format_table_pipe_tuple_wrapped(self, tuple_wrapped_data):
        """튜플로 감싸진 데이터 처리 테스트 - 파이프 포맷"""
        result = format_table_pipe(tuple_wrapped_data)
        
        # 헤더 확인
        assert "bank_nm | acct_no | trsc_amt | balance" in result
        
        # 데이터 행 확인
        assert "Bank A | 11111111 | 500.25 | 2000.00" in result
        assert "Bank B | 22222222 | 1500.75 | 8000.50" in result

    def test_format_table_html_tuple_wrapped(self, tuple_wrapped_data):
        """튜플로 감싸진 데이터 처리 테스트 - HTML 포맷"""
        result = format_table_html(tuple_wrapped_data)
        
        # 테이블 태그 확인
        assert "<table>" in result
        assert "</table>" in result
        
        # 헤더 확인
        assert "<th>bank_nm</th>" in result
        assert "<th>acct_no</th>" in result
        
        # 데이터 행 확인
        assert "<td>Bank A</td>" in result
        assert "<td>11111111</td>" in result

    def test_format_table_pipe_empty(self):
        """빈 데이터 처리 테스트 - 파이프 포맷"""
        result = format_table_pipe([])
        assert "(데이터 없음)" in result

    def test_format_table_pipe_invalid_type(self):
        """유효하지 않은 데이터 타입 처리 테스트 - 파이프 포맷"""
        result = format_table_pipe("not a list or tuple")
        assert "(변환할 수 없는 데이터 형식)" in result

    def test_format_table_html_invalid_type(self):
        """유효하지 않은 데이터 타입 처리 테스트 - HTML 포맷"""
        result = format_table_html("not a list or tuple")
        assert "<table>" in result
        assert "(변환할 수 없는 데이터 형식)" in result
        assert "</table>" in result

    def test_format_table_pipe_nested(self, nested_data):
        """중첩 구조 데이터 평탄화 테스트 - 파이프 포맷"""
        result = format_table_pipe(nested_data)
        
        # 평탄화된 데이터의 컬럼 확인
        assert "col1 | col2" in result
        
        # 평탄화된 데이터 값 확인
        assert "value1 | value2" in result
        assert "value7 | value8" in result

    def test_format_table_html_nested(self, nested_data):
        """중첩 구조 데이터 평탄화 테스트 - HTML 포맷"""
        result = format_table_html(nested_data)
        
        # 평탄화된 데이터의 컬럼 확인
        assert "<th>col1</th>" in result
        assert "<th>col2</th>" in result
        
        # 평탄화된 데이터 값 확인
        assert "<td>value3</td>" in result
        assert "<td>value6</td>" in result

    def test_format_table_pipe_truncation(self, large_data):
        """대용량 데이터 자동 축소 테스트 - 파이프 포맷"""
        result = format_table_pipe(large_data)
        
        # 처음 5개 항목은 표시
        assert "Item 1" in result
        assert "Item 5" in result
        
        # 중간 생략 메시지 확인
        assert "... (중간 생략) ..." in result
        
        # 마지막 5개 항목은 표시
        assert "Item 12" in result
        assert "Item 8" in result

    def test_format_table_html_truncation(self, large_data):
        """대용량 데이터 자동 축소 테스트 - HTML 포맷"""
        result = format_table_html(large_data)
        
        # 처음 10개 항목은 표시
        assert "Item 1" in result
        assert "Item 10" in result
        
        # 생략 메시지 확인
        assert "... 외 2행 생략 ..." in result
        
        # 11, 12번 항목은 생략됨
        assert "Item 11" not in result
        assert "Item 12" not in result
        
    def test_real_world_query_result(self):
        """실제 쿼리 결과와 같은 형태의 데이터 테스트"""
        # 실제 query_result 형태를 모방
        query_result = (
            [
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
                },
                {
                    "bank_nm": "Bank C",
                    "acct_no": "33333333333",
                    "trsc_amt": Decimal("12310.75"),
                    "balance": Decimal("8670.50")
                }
            ],
        )
        
        # 파이프 포맷 테스트
        pipe_result = format_table_pipe(query_result)
        assert "bank_nm | acct_no | trsc_amt | balance" in pipe_result
        assert "Bank A | 11111111 | 500.25 | 2000.00" in pipe_result
        assert "Bank C | 33333333333 | 12310.75 | 8670.50" in pipe_result
        
        # HTML 포맷 테스트
        html_result = format_table_html(query_result)
        assert "<th>bank_nm</th>" in html_result
        assert "<td>Bank B</td>" in html_result
        assert "<td>33333333333</td>" in html_result