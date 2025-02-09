import re
from statistics import mean, mode, StatisticsError
from typing import List, Dict, Any

def fulfill_fstring(fstring_answer: str, result: List[Dict[str, Any]], column_list: List[str]) -> str:
    """
    f-string 형태의 응답에서 함수를 실제 계산값으로 대체합니다.
    
    지원하는 함수들:
    - sum(column): 컬럼의 모든 값을 합산
    - average(column): 컬럼의 평균값을 계산
    - count(column): 컬럼의 non-null 값 개수를 계산
    - unique(column): 컬럼의 중복 제거된 값들을 나열
    - mode(column): 컬럼의 최빈값을 반환
    - max(column): 컬럼의 최대값을 반환
    - min(column): 컬럼의 최소값을 반환
    - value(column): 컬럼의 모든 값을 나열
    """
    if fstring_answer.startswith('f"') and fstring_answer.endswith('"'):
        fstring_answer = fstring_answer[2:-1]
    elif fstring_answer.startswith("f'") and fstring_answer.endswith("'"):
        fstring_answer = fstring_answer[2:-1]
    
    def calculate_sum(column: str) -> int:
        """특정 컬럼의 모든 값을 합산"""
        return sum(float(row[column]) for row in result if column in row and row[column] is not None)
    
    def calculate_average(column: str) -> float:
        """특정 컬럼의 평균값을 계산"""
        values = [float(row[column]) for row in result if column in row and row[column] is not None]
        return mean(values)
    
    def calculate_count(column: str) -> int:
        """특정 컬럼의 값 개수를 계산"""
        return len([row[column] for row in result if column in row and row[column] is not None])
    
    def get_unique_values(column: str) -> str:
        """특정 컬럼의 중복 제거된 값들을 반환"""
        unique_values = set(str(row[column]) for row in result if column in row and row[column] is not None)
        return ', '.join(sorted(unique_values))

    def get_mode(column: str) -> str:
        """특정 컬럼의 최빈값을 반환"""
        values = [str(row[column]) for row in result if column in row and row[column] is not None]
        try:
            return mode(values)
        except StatisticsError:
            # 최빈값이 여러 개인 경우 모두 반환
            freq_dict = {}
            for value in values:
                freq_dict[value] = freq_dict.get(value, 0) + 1
            max_freq = max(freq_dict.values())
            modes = [val for val, freq in freq_dict.items() if freq == max_freq]
            return ', '.join(sorted(modes))

    def get_max(column: str) -> Any:
        """특정 컬럼의 최대값을 반환"""
        values = [row[column] for row in result if column in row and row[column] is not None]
        try:
            # 숫자로 변환 가능한 경우
            numeric_values = [float(val) for val in values]
            return format(max(numeric_values), ',')
        except ValueError:
            # 문자열인 경우
            return max(values)

    def get_min(column: str) -> Any:
        """특정 컬럼의 최소값을 반환"""
        values = [row[column] for row in result if column in row and row[column] is not None]
        try:
            # 숫자로 변환 가능한 경우
            numeric_values = [float(val) for val in values]
            return format(min(numeric_values), ',')
        except ValueError:
            # 문자열인 경우
            return min(values)

    def get_all_values(column: str) -> str:
        """특정 컬럼의 모든 값을 나열"""
        values = [str(row[column]) for row in result if column in row and row[column] is not None]
        try:
            # 숫자로 변환 가능한 경우 천 단위 구분자 추가
            numeric_values = [format(float(val), ',') for val in values]
            return ', '.join(numeric_values)
        except ValueError:
            # 문자열인 경우 그대로 반환
            return ', '.join(values)

    # 함수와 컬럼명을 찾는 정규표현식 패턴
    pattern = r'\{(sum|average|count|unique|mode|max|min|value)\(([\w_]+)\)\}'
    
    def replace_function(match):
        func_name = match.group(1)
        column = match.group(2)
        
        # 컬럼이 유효한지 확인
        if column not in column_list:
            raise ValueError(f"Invalid column name: {column}")
        
        # 함수별 계산 수행
        if func_name == 'sum':
            value = calculate_sum(column)
            return format(value, ',')
        elif func_name == 'average':
            value = calculate_average(column)
            return format(value, ',.2f')
        elif func_name == 'count':
            value = calculate_count(column)
            return format(value, ',')
        elif func_name == 'unique':
            return get_unique_values(column)
        elif func_name == 'mode':
            return get_mode(column)
        elif func_name == 'max':
            return get_max(column)
        elif func_name == 'min':
            return get_min(column)
        elif func_name == 'value':
            return get_all_values(column)
        else:
            raise ValueError(f"Unknown function: {func_name}")
    
    # 모든 함수를 계산값으로 대체
    final_answer = re.sub(pattern, replace_function, fstring_answer)
    
    return final_answer