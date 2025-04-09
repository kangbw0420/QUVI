import pytest
import pandas as pd
import os
from utils.table.calc_table import eval_fstring_template, SafeExpressionEvaluator

@pytest.fixture
def sample_data():
    """테스트용 데이터프레임 생성"""
    return pd.DataFrame({
        'age': [25, 30, 35, 40],
        'name': ['Alice', 'Bob', 'Charlie', 'David'],
        'salary': [50000, 60000, 75000, 90000],
        'department': ['HR', 'IT', 'IT', 'Finance'],
        'is_manager': [False, True, False, True]
    })

class TestSafeExpressionEvaluator:
    """기본 기능 테스트"""
    
    def test_basic_sum(self, sample_data):
        expr = "총 급여는 {df['salary'].sum()}원"
        result = eval_fstring_template(f"f'{expr}'", sample_data)
        assert "275000" in result  # 50000+60000+75000+90000

    def test_column_len(self, sample_data):
        expr = "직원 수: {len(df['name'])}명"
        result = eval_fstring_template(f"f'{expr}'", sample_data)
        assert "4명" in result

    def test_tolist_conversion(self, sample_data):
        expr = "이름 목록: {df['name'].tolist()}"
        result = eval_fstring_template(f"f'{expr}'", sample_data)
        assert "['Alice', 'Bob', 'Charlie', 'David']" in result

    def test_sort_values(self, sample_data):
        expr = "고액연봉 순: {df.sort_values('salary', ascending=False)['name'].tolist()}"
        result = eval_fstring_template(f"f'{expr}'", sample_data)
        assert "['David', 'Charlie', 'Bob', 'Alice']" in result

class TestAllowedOperations:
    """허용된 함수/메서드 테스트"""
    
    def test_mean_function(self, sample_data):
        expr = "평균 연봉: {df['salary'].mean()}"
        result = eval_fstring_template(f"f'{expr}'", sample_data)
        assert "68750.0" in result

    def test_boolean_indexing(self, sample_data):
        expr = "관리자 수: {len(df[df['is_manager']])}"
        result = eval_fstring_template(f"f'{expr}'", sample_data)
        assert "2" in result

class TestSecurityRestrictions:
    """보안 제한 테스트"""
    
    def test_os_system_blocked(self, sample_data):
        expr = "{__import__('os').system('ls')}"
        result = eval_fstring_template(f"f'{expr}'", sample_data)
        assert "허용되지 않" in result

    def test_private_attribute_access(self, sample_data):
        expr = "{df._is_mixed_type}"
        result = eval_fstring_template(f"f'{expr}'", sample_data)
        assert "속성 '_is_mixed_type'는 허용되지 않았습니다" in result

    def test_forbidden_method(self, sample_data):
        expr = "{df.to_sql('test')}"
        result = eval_fstring_template(f"f'{expr}'", sample_data)
        assert "'to_sql'는 허용되지 않" in result

class TestEdgeCases:
    """예외 상황 테스트"""
    
    def test_empty_dataframe(self):
        expr = "총 개수: {len(df)}"
        result = eval_fstring_template("f'"+expr+"'", pd.DataFrame())
        assert "0" in result

    def test_invalid_column(self, sample_data):
        expr = "{df['invalid_column'].sum()}"
        result = eval_fstring_template(f"f'{expr}'", sample_data)
        assert "[오류: 'invalid_column']" in result

    def test_malformed_expression(self, sample_data):
        expr = "{df['salary'].sum(()}"
        result = eval_fstring_template(f"f'{expr}'", sample_data)
        assert "was never closed" in result

class TestFormatting:
    """형식 지정 테스트"""
    
    def test_currency_formatting(self, sample_data):
        expr = "총 급여: {df['salary'].sum():,}원"
        result = eval_fstring_template(f"f'{expr}'", sample_data)
        assert "275,000원" in result

    def test_float_precision(self, sample_data):
        expr = "평균 연봉: {df['salary'].mean():.2f}"
        result = eval_fstring_template(f"f'{expr}'", sample_data)
        assert "68750.00" in result

    def test_dict_conversion(self, sample_data):
        expr = "이름-연봉 매핑: {dict(zip(df['name'], df['salary']))}"
        result = eval_fstring_template(f"f'{expr}'", sample_data)
        assert "'Alice': 50000" in result