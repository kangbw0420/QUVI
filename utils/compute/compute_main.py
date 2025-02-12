import re
from typing import List, Dict, Any
from utils.compute.formatter import format_number
from utils.compute.eval_func import parse_function_params, eval_function

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
    
    # Check if expression contains operators
    if any(op in expression for op in ['+', '-', '*', '/']):
        try:
            pattern = r'(\w+(?:\.\w+)?)\((.*?)\)'
            replaced_values = []
            primary_func_name = None  # 첫 번째 함수명 저장

            while True:
                func_match = re.search(pattern, expression)
                if not func_match:
                    break
                    
                func_name, param_str = func_match.groups()
                if primary_func_name is None:
                    primary_func_name = func_name  # 첫 번째 함수명 캡처
                params = parse_function_params(param_str)
                value = eval_function(func_name, params, result, column_list)
                
                replaced_values.append({
                    'value': value, 
                    'func_name': func_name,
                    'params': params 
                })
                 
                expression = expression[:func_match.start()] + str(value) + expression[func_match.end():]
                 
            final_value = eval(expression)
            all_params = []
            for val_info in replaced_values:
                all_params.extend(val_info['params'])
             
            # 첫 번째 함수명을 format_number에 전달
            return format_number(final_value, "", primary_func_name, all_params)
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    # Handle single function
    func_match = re.match(r'(\w+(?:\.\w+)?)\((.*)\)', expression)
    if not func_match:
        return '{' + expression + '}'
        
    func_name, param_str = func_match.groups()
    params = parse_function_params(param_str)
    
    try:
        value = eval_function(func_name, params, result, column_list)
        # Only format numeric results
        if isinstance(value, (int, float)):
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