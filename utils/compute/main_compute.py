import re
from typing import List, Dict, Any
from decimal import Decimal
from utils.compute.formatter import format_number
from utils.compute.computer import parse_function_params, compute_function
from utils.compute.detector import detect_computed_column, split_by_operators, calculate_with_operator

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

def handle_computed_column(match: re.Match, result: List[Dict[str, Any]], column_list: List[str]) -> str:
    """Handle expressions inside curly braces with support for computed columns"""
    expression = match.group(1)
    
    try:
        return handle_math_expression(match, result, column_list)
    except ValueError as e:
        error_msg = str(e)
        is_computed, func_name, _ = detect_computed_column(error_msg, column_list)
        
        if is_computed:
            # Replace function(column_name) with value(function_name)
            modified_expression = f"value({func_name})"
            modified_match = type('Match', (), {'group': lambda x: modified_expression})()
            return handle_math_expression(modified_match, result, column_list)
        raise

def compute_fstring(fstring_answer: str, result: List[Dict[str, Any]], column_list: List[str]) -> str:
    if fstring_answer.startswith('f"') and fstring_answer.endswith('"'):
        fstring_answer = fstring_answer[2:-1]
    elif fstring_answer.startswith("f'") and fstring_answer.endswith("'"):
        fstring_answer = fstring_answer[2:-1]

    pattern = r'\{([^}]+)\}'
    processed_answer = re.sub(pattern, lambda m: handle_computed_column(m, result, column_list), fstring_answer)
    
    # "Error: "가 포함되어 있는지 체크
    if "Error: " in processed_answer:
        return (
            "요청주신 질문에 대한 데이터는 아래 표와 같습니다.\n\n"
            "...라고 정식 출시 때는 나갈 예정입니다.\U0001F605 현재는 베타 기간이니 에러난 답변도 보시지요.\U0001f600:\n\n"
            f"{processed_answer}"
        )
    return processed_answer