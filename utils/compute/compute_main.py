import re
from typing import List, Dict, Any
from decimal import Decimal
from utils.compute.formatter import format_number
from utils.compute.computer import parse_function_params, compute_function

def detect_computed_column(error_msg: str, column_list: List[str]) -> tuple[bool, str, str]:
    """Detect if the error is from trying to access a computed column directly
    Args:
        error_msg: The error message containing "Invalid column name: xxx"
        column_list: List of available columns including computed ones
    Returns:
        tuple[bool, str, str]: (is_computed, function_name, column_name)
    """
    # Extract the invalid column name from error
    match = re.search(r"Invalid column name: (\w+)", error_msg)
    if not match:
        return False, "", ""
        
    invalid_col = match.group(1)
    
    # Check if any computed columns exist
    computed_cols = [col for col in column_list if col in ['sum', 'count', 'average']]
    if not computed_cols:
        return False, "", ""
        
    # Look for function pattern in the original expression
    for func in ['sum', 'count', 'average']:
        if f"{func}({invalid_col})" in error_msg:
            if func in computed_cols:
                return True, func, invalid_col
                
    return False, "", ""

def handle_math_expression(match: re.Match, result: List[Dict[str, Any]], column_list: List[str]) -> str:
    """Handle expressions inside curly braces with support for nested functions"""
    expression = match.group(1)
    
    # 단일 함수 호출 패턴
    func_pattern = r'(\w+(?:\.\w+)?)\((.*?)\)'
    
    # 연산자가 있는지 확인
    has_operators = any(op in expression for op in ['+', '-', '*', '/'])
    
    if has_operators:
        # 모든 함수 호출을 찾아서 평가
        while True:
            func_match = re.search(func_pattern, expression)
            if not func_match:
                break
                
            func_name, param_str = func_match.groups()
            params = parse_function_params(param_str)
            
            try:
                # 함수 결과를 계산
                value = compute_function(func_name, params, result, column_list)
                # 결과를 문자열로 변환하여 표현식에 대체
                expression = expression[:func_match.start()] + str(value) + expression[func_match.end():]
                
            except Exception as e:
                return f"Error: {str(e)}"
        
        # 모든 함수가 평가된 후의 최종 식을 처리
        try:
            # 산술 연산을 위한 가상의 함수 생성
            calc_params = [expression]
            final_value = compute_function('value', calc_params, result, column_list)
            return format_number(final_value, "", None, None)
        except Exception as e:
            return f"Error: {str(e)}"
            
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
                                    params if len(params) > 1 else None)
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
    return re.sub(pattern, lambda m: handle_computed_column(m, result, column_list), fstring_answer)