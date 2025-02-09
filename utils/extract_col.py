from typing import List, Dict, Any
import re
from statistics import mean

def extract_col(result: List[Dict[str, Any]]) -> List[str]:
    """
    데이터프레임 형태의 쿼리 결과에서 컬럼명(키)을 추출합니다.
    Returns:
        List[str]: 추출된 컬럼명 리스트
    Raises:
        ValueError: result가 비어있거나 유효하지 않은 형식인 경우
    """
    # 입력 검증
    if not result:
        raise ValueError("Result list is empty")
        
    if not isinstance(result, list):
        raise ValueError("Result must be a list")
        
    if not isinstance(result[0], dict):
        raise ValueError("Result items must be dictionaries")
        
    # 첫 번째 레코드에서 키(컬럼명)를 추출
    # 모든 레코드는 동일한 구조를 가지므로 첫 번째 레코드만 확인
    columns = list(result[0].keys())
    
    if not columns:
        raise ValueError("No columns found in result")
        
    return columns

def fulfill_fstring(fstring_answer: str, result: List[Dict[str, Any]], column_list: List[str]) -> str:
    """
    f-string 형태의 응답에서 함수를 실제 계산값으로 대체합니다.
    
    Args:
        fstring_answer (str): 함수를 포함한 f-string 형태의 응답
        result (List[Dict[str, Any]]): SQL 쿼리 실행 결과
        column_list (List[str]): 컬럼명 리스트
        
    Returns:
        str: 계산된 값이 대체된 최종 응답
        
    Example:
        >>> fstring = "수시입출계좌 잔액은 {sum(acct_bal_amt)}입니다."
        >>> fulfill_fstring(fstring, result, columns)
        "수시입출계좌 잔액은 11965052입니다."
    """
    if fstring_answer.startswith('f"') and fstring_answer.endswith('"'):
        fstring_answer = fstring_answer[2:-1]
    elif fstring_answer.startswith("f'") and fstring_answer.endswith("'"):
        fstring_answer = fstring_answer[2:-1]
    
    def calculate_sum(column: str) -> int:
        """특정 컬럼의 모든 값을 합산"""
        return sum(float(row[column]) for row in result if row[column] is not None)
    
    def calculate_average(column: str) -> float:
        """특정 컬럼의 평균값을 계산"""
        values = [float(row[column]) for row in result if row[column] is not None]
        return mean(values)
    
    def calculate_count(column: str) -> int:
        """특정 컬럼의 값 개수를 계산"""
        return len([row[column] for row in result if row[column] is not None])
    
    def get_unique_values(column: str) -> str:
        """특정 컬럼의 중복 제거된 값들을 반환"""
        unique_values = set(str(row[column]) for row in result if row[column] is not None)
        return ', '.join(sorted(unique_values))

    # 함수와 컬럼명을 찾는 정규표현식 패턴
    pattern = r'\{(sum|average|count|unique)\(([\w_]+)\)\}'
    
    def replace_function(match):
        func_name = match.group(1)
        column = match.group(2)
        
        # 컬럼이 유효한지 확인
        if column not in column_list:
            raise ValueError(f"Invalid column name: {column}")
        
        # 함수별 계산 수행
        if func_name == 'sum':
            value = calculate_sum(column)
            return format(value, ',')  # 천 단위 구분자 추가
        elif func_name == 'average':
            value = calculate_average(column)
            return format(value, ',.2f')  # 소수점 2자리까지 표시
        elif func_name == 'count':
            value = calculate_count(column)
            return format(value, ',')
        elif func_name == 'unique':
            return get_unique_values(column)
        else:
            raise ValueError(f"Unknown function: {func_name}")
    
    # 모든 함수를 계산값으로 대체
    final_answer = re.sub(pattern, replace_function, fstring_answer)
    
    return final_answer