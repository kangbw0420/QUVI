import re
from statistics import mean, mode, StatisticsError
from typing import List, Dict, Any

currency_list = [
    "AED", "ARS", "AUD", "BDT", "BHD", "BND", "BRL", "CAD", "CHF", "CLP",
    "CNH", "CNY", "COP", "CZK", "DKK", "EGP", "ETB", "EUR", "FJD", "GBP",
    "HKD", "HUF", "IDR", "ILS", "INR", "JOD", "JPY", "KRW", "KES", "KHR",
    "KWD", "KZT", "LKR", "LYD", "MMK", "MNT", "MOP", "MXN", "MYR", "NOK",
    "NPR", "NZD", "OMR", "PHP", "PKR", "PLN", "QAR", "RON", "RUB", "SAR",
    "SEK", "SGD", "THB", "TRY", "TWD", "USD", "UZS", "VND", "ZAR"
]

def should_use_decimals(column: str, func_name: str) -> bool:
    """Determine if a column should use decimal places in its formatting"""
    no_decimal_funcs = {'count'}
    if func_name in no_decimal_funcs:
        return False
        
    must_decimal_column = {'intr_rate'}
    if column in must_decimal_column:
        return True
        
    for curr in currency_list:
        if curr != 'KRW' and column.startswith(f"{curr}_"):
            return True
            
    return False

def format_number(value: float, column: str, func_name: str = '') -> str:
    """Format a number according to the column and function rules"""
    try:
        float_value = float(value)
        if should_use_decimals(column, func_name):
            return format(round(float_value, 2), ',.2f')
        else:
            return format(round(float_value), ',')
    except ValueError:
        return str(value)

def calculate_value(func_name: str, column: str, result: List[Dict[str, Any]], column_list: List[str]) -> float:
    """Calculate the value for a single function"""
    if column not in column_list:
        raise ValueError(f"Invalid column name: {column}")
        
    if func_name == 'sum':
        return sum(float(row[column]) for row in result if column in row and row[column] is not None)
    elif func_name == 'count':
        return float(len([row[column] for row in result if column in row and row[column] is not None]))
    elif func_name == 'average':
        values = [float(row[column]) for row in result if column in row and row[column] is not None]
        return mean(values)
    else:
        raise ValueError(f"Unsupported function for calculation: {func_name}")

def evaluate_expression(expression: str, result: List[Dict[str, Any]], column_list: List[str]) -> float:
    """Evaluate a mathematical expression containing functions"""
    # Replace functions with their calculated values
    pattern = r'(sum|count|average)\(([\w_]+)\)'
    while True:
        match = re.search(pattern, expression)
        if not match:
            break
        func_name, column = match.groups()
        value = calculate_value(func_name, column, result, column_list)
        expression = expression[:match.start()] + str(float(value)) + expression[match.end():]
    
    # Evaluate the resulting mathematical expression
    return float(eval(expression))

def detect_computed_column(error_msg: str, column_list: List[str]) -> tuple[bool, str, str]:
    """
    Detect if the error is from trying to access a computed column directly
    
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

def handle_math_expression(match: re.Match, result: List[Dict[str, Any]], column_list: List[str]) -> str:
    """Handle expressions inside curly braces"""
    expression = match.group(1)
    
    # Check if expression contains operators
    if any(op in expression for op in ['+', '-', '*', '/']):
        try:
            # Get first function's column and name for formatting
            first_func = re.search(r'(sum|count|average)\(([\w_]+)\)', expression)
            if first_func:
                func_name, column = first_func.groups()
            else:
                func_name, column = '', ''
            
            value = evaluate_expression(expression, result, column_list)
            return format_number(value, column, func_name)
        except Exception as e:
            return f"Error: {str(e)}"
    
    # Handle single function
    pattern = r'(sum|count|average|unique|mode|max|min|value)\(([\w_]+)\)'
    match = re.match(pattern, expression)
    if not match:
        return '{' + expression + '}'
        
    func_name, column = match.groups()
    
    if column not in column_list:
        raise ValueError(f"Invalid column name: {column}")
    
    if func_name == 'sum':
        total = sum(float(row[column]) for row in result if column in row and row[column] is not None)
        return format_number(total, column, func_name)
    elif func_name == 'average':
        values = [float(row[column]) for row in result if column in row and row[column] is not None]
        avg = mean(values)
        return format_number(avg, column, func_name)
    elif func_name == 'count':
        count = len([row[column] for row in result if column in row and row[column] is not None])
        return format_number(count, column, func_name)
    elif func_name == 'unique':
        unique_values = set(str(row[column]) for row in result if column in row and row[column] is not None)
        return ', '.join(sorted(unique_values))
    elif func_name == 'mode':
        values = [str(row[column]) for row in result if column in row and row[column] is not None]
        try:
            return mode(values)
        except StatisticsError:
            freq_dict = {}
            for value in values:
                freq_dict[value] = freq_dict.get(value, 0) + 1
            max_freq = max(freq_dict.values())
            modes = [val for val, freq in freq_dict.items() if freq == max_freq]
            return ', '.join(sorted(modes))
    elif func_name == 'max':
        values = [row[column] for row in result if column in row and row[column] is not None]
        try:
            numeric_values = [float(val) for val in values]
            max_val = max(numeric_values)
            return format_number(max_val, column, func_name)
        except ValueError:
            return max(values)
    elif func_name == 'min':
        values = [row[column] for row in result if column in row and row[column] is not None]
        try:
            numeric_values = [float(val) for val in values]
            min_val = min(numeric_values)
            return format_number(min_val, column, func_name)
        except ValueError:
            return min(values)
    elif func_name == 'value':
        values = [row[column] for row in result if column in row and row[column] is not None]
        try:
            numeric_values = [format_number(float(val), column, func_name) for val in values]
            return ', '.join(numeric_values)
        except ValueError:
            return ', '.join(str(val) for val in values)
    else:
        raise ValueError(f"Unknown function: {func_name}")

def fulfill_fstring(fstring_answer: str, result: List[Dict[str, Any]], column_list: List[str]) -> str:
    if fstring_answer.startswith('f"') and fstring_answer.endswith('"'):
        fstring_answer = fstring_answer[2:-1]
    elif fstring_answer.startswith("f'") and fstring_answer.endswith("'"):
        fstring_answer = fstring_answer[2:-1]

    pattern = r'\{([^}]+)\}'
    return re.sub(pattern, lambda m: handle_computed_column(m, result, column_list), fstring_answer)