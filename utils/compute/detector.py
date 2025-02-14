import re
from typing import List, Tuple, Dict, Any
from decimal import Decimal

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

def split_by_operators(expression: str) -> List[Tuple[str, str]]:
    """수식을 연산자를 기준으로 분리하고 항목과 연산자 리스트를 반환"""
    parts = []
    current_part = ""
    current_operator = ""
    paren_count = 0
    
    for char in expression:
        if char == '(':
            paren_count += 1
            current_part += char
        elif char == ')':
            paren_count -= 1
            current_part += char
        elif char in ['+', '-', '*', '/'] and paren_count == 0:
            if current_part:
                parts.append((current_part.strip(), current_operator))
            current_part = ""
            current_operator = char
        else:
            current_part += char
            
    if current_part:
        parts.append((current_part.strip(), current_operator))
        
    return parts

def calculate_with_operator(value1: Decimal, value2: Decimal, operator: str) -> Decimal:
    """두 값에 연산자를 적용하여 계산"""
    if operator == '+':
        return value1 + value2
    elif operator == '-':
        return value1 - value2
    elif operator == '*':
        return value1 * value2
    elif operator == '/':
        if value2 == 0:
            raise ValueError("Division by zero")
        return value1 / value2
    else:
        raise ValueError(f"Unknown operator: {operator}")