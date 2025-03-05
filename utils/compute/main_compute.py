import re
from typing import List, Dict, Any
from decimal import Decimal
from utils.compute.formatter import format_number
from utils.compute.computer import parse_function_params, compute_function
from utils.compute.detector import split_by_operators, calculate_with_operator

def handle_math_expression(match: re.Match, result: List[Dict[str, Any]], column_list: List[str]) -> str:
    expression = match.group(1)
    func_pattern = r'(\w+(?:\.\w+)?)\((.*?)\)'
    
    has_operators = any(op in expression for op in ['+', '-', '*', '/'])
    
    if has_operators:
        # 수식을 연산자를 기준으로 분리
        parts = split_by_operators(expression)
        all_params = []  # 전체 연산에 사용된 모든 파라미터 수집
        
        try:
            # 첫 번째 부분 계산
            first_part, _ = parts[0]
            func_match = re.match(func_pattern, first_part)
            if not func_match:
                raise ValueError(f"Invalid expression part: {first_part}")
                
            func_name, param_str = func_match.groups()
            params = parse_function_params(param_str)
            all_params.extend(params)  # 파라미터 수집
            current_value = compute_function(func_name, params, result, column_list)
            
            # 나머지 부분들 순차적으로 계산
            for part, operator in parts[1:]:
                func_match = re.match(func_pattern, part)
                if not func_match:
                    raise ValueError(f"Invalid expression part: {part}")
                    
                func_name, param_str = func_match.groups()
                params = parse_function_params(param_str)
                all_params.extend(params)  # 파라미터 수집
                next_value = compute_function(func_name, params, result, column_list)
                
                # 연산자를 적용하여 계산
                current_value = calculate_with_operator(current_value, next_value, operator)
            
            # 수집된 모든 파라미터 전달
            return format_number(current_value, "", func_name, all_params)
            
        except Exception as e:
            return f"Error in calculation: {str(e)}"
            
    else:
        # 단일 함수 처리
        func_match = re.match(func_pattern, expression)
        if not func_match:
            return '{' + expression + '}'
            
        func_name, param_str = func_match.groups()
        params = parse_function_params(param_str)
        
        try:
            value = compute_function(func_name, params, result, column_list)
            if isinstance(value, (int, float, Decimal)):
                return format_number(value,
                                  params[0] if len(params) == 1 else "",
                                  func_name,
                                  params)  # 여기도 params 전달 추가
            return str(value)
        except Exception as e:
            return f"Error: {str(e)}"

def handle_computed_column(expression: str, result: List[Dict[str, Any]], column_list: List[str]) -> str:
    """계산식 표현식에서 미리 계산된 컬럼(sum, count, average 등)을 처리합니다.
    
    Args:
        expression: 처리할 표현식 문자열
        result: SQL 쿼리 실행 결과 데이터의 리스트
        column_list: 결과 데이터에서 사용 가능한 컬럼명 리스트
        
    Returns:
        str: 처리된 결과 문자열. 계산된 컬럼이 있으면 해당 값 반환, 아니면 원래 표현식 반환
    """
    # expression이 그 자체로 column_list에 있는지 먼저 확인
    if expression in column_list and len(result) == 1:
        try:
            return str(int(result[0][expression]))
        except (ValueError, TypeError):
            return str(result[0][expression])
    
    # 계산 함수 목록
    computed_funcs = ['sum', 'count', 'average']
    
    # 컬럼 리스트에 계산 함수가 포함된 이름이 있는지 확인
    computed_cols = []
    for col in column_list:
        for func in computed_funcs:
            if func in col:
                computed_cols.append(col)
                break
    
    if computed_cols and len(result) == 1:
        # 표현식에서 계산된 컬럼이 사용되었는지 확인
        for col in computed_cols:
            if col == expression:
                # 정확히 일치하는 경우 바로 해당 값 반환
                computed_value = result[0].get(col)
                if computed_value is not None:
                    return str(computed_value)
    
    # 계산된 컬럼이 아니거나 결과가 여러 개인 경우, 기존 handle_math_expression 호출
    try:
        match = type('Match', (), {'group': lambda *args: expression})()
        return handle_math_expression(match, result, column_list)
    except ValueError as e:
        # 에러 처리
        return f"Error: {str(e)}"

def compute_fstring(fstring_answer: str, result: List[Dict[str, Any]], column_list: List[str]) -> str:
    # 작은 따옴표와 큰 따옴표 문구에 모두 대응. 괄호 내부만 뽑아냄
    if fstring_answer.startswith('f"') and fstring_answer.endswith('"'):
        fstring_answer = fstring_answer[2:-1]
    elif fstring_answer.startswith("f'") and fstring_answer.endswith("'"):
        fstring_answer = fstring_answer[2:-1]

    # 중괄호 안에 있는 걸 찾아내기
    pattern = r'\{([^}]+)\}'
    processed_answer = re.sub(pattern, lambda m: handle_computed_column(m.group(1), result, column_list), fstring_answer)
    
    # "Error: "가 포함되어 있는지 체크
    if "Error: " in processed_answer:
        return (
            "요청주신 질문에 대한 데이터는 아래 표와 같습니다.\n\n"
            # "...라고 정식 출시 때는 나갈 예정입니다.\U0001F605 현재는 베타 기간이니 에러난 답변도 보시지요.\U0001f600:\n\n"
            # f"{processed_answer}"
        )
    if "Division by zero" in processed_answer:
        return (
            "요청주신 질문을 처리하는 과정에서 0으로 나눠야 하는 상황이 발생했습니다. 이는 불가능하므로, 질문 혹은 데이터를 확인해주시면 감사하겠습니다.\n\n"
            f"{processed_answer}"
        )
    return processed_answer