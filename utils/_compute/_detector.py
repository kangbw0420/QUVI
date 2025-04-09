import re
from typing import List, Tuple, Dict, Any
from decimal import Decimal

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