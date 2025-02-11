import re
from statistics import mean, mode, StatisticsError
from typing import List, Dict, Any, Union

currency_list = [
    "AED", "ARS", "AUD", "BDT", "BHD", "BND", "BRL", "CAD", "CHF", "CLP",
    "CNH", "CNY", "COP", "CZK", "DKK", "EGP", "ETB", "EUR", "FJD", "GBP",
    "HKD", "HUF", "IDR", "ILS", "INR", "JOD", "JPY", "KRW", "KES", "KHR",
    "KWD", "KZT", "LKR", "LYD", "MMK", "MNT", "MOP", "MXN", "MYR", "NOK",
    "NPR", "NZD", "OMR", "PHP", "PKR", "PLN", "QAR", "RON", "RUB", "SAR",
    "SEK", "SGD", "THB", "TRY", "TWD", "USD", "UZS", "VND", "ZAR"
]

def should_use_decimals(column: str, func_name: str, params: List[str] = None) -> bool:
    """Determine if a column should use decimal places in its formatting"""
    no_decimal_funcs = {'count'}
    if func_name in no_decimal_funcs:
        return False

    must_decimal_column = {'intr_rate'}

    if params:
        for param in params:
            if param in must_decimal_column:
                return True
            for curr in currency_list:
                if curr != 'KRW' and param.startswith(f"{curr}_"):
                    return True

    if column in must_decimal_column:
        return True
        
    for curr in currency_list:
        if curr != 'KRW' and column.startswith(f"{curr}_"):
            return True
            
    return False

def format_number(value: float, column: str, func_name: str = '', params: List[str] = None) -> str:
    """Format a number according to the column and function rules"""
    try:
        if func_name in ['count']:
            return format(int(value), ',')

        float_value = float(value)
        if should_use_decimals(column, func_name, params):
            return format(round(float_value, 2), ',.2f')
        else:
            return format(round(float_value), ',')
    except ValueError:
        return str(value)


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


def fulfill_fstring(fstring_answer: str, result: List[Dict[str, Any]], column_list: List[str]) -> str:
    if fstring_answer.startswith('f"') and fstring_answer.endswith('"'):
        fstring_answer = fstring_answer[2:-1]
    elif fstring_answer.startswith("f'") and fstring_answer.endswith("'"):
        fstring_answer = fstring_answer[2:-1]

    pattern = r'\{([^}]+)\}'
    return re.sub(pattern, lambda m: handle_computed_column(m, result, column_list), fstring_answer)


def parse_function_params(param_str: str) -> List[str]:
    """Parse function parameters, handling nested functions and multiple parameters"""
    params = []
    current_param = ""
    paren_count = 0
    
    for char in param_str:
        if char == '(' :
            paren_count += 1
            current_param += char
        elif char == ')':
            paren_count -= 1
            current_param += char
        elif char == ',' and paren_count == 0:
            params.append(current_param.strip())
            current_param = ""
        else:
            current_param += char
            
    if current_param:
        params.append(current_param.strip())
        
    return params

def eval_function(func_name: str, params: List[str], result: List[Dict[str, Any]], column_list: List[str]) -> Union[float, str]:
    """Evaluate a function with its parameters"""
    # Handle nested functions first
    if func_name == 'sum':
        if len(params) != 1:
            raise ValueError("sum function requires exactly one parameter")
    elif func_name == 'average':
        if len(params) != 1:
            raise ValueError("average function requires exactly one parameter")
    elif func_name == 'sumproduct':
        if len(params) != 2:
            raise ValueError("sumproduct requires exactly two parameters")
    elif func_name == 'count':
        if len(params) != 1:
            raise ValueError("count function requires exactly one parameter")
    elif func_name == 'unique':
        if len(params) != 1:
            raise ValueError("unique function requires exactly one parameter")
    elif func_name == 'mode':
        if len(params) != 1:
            raise ValueError("mode function requires exactly one parameter")
    elif func_name == 'max':
        if len(params) != 1:
            raise ValueError("average function requires exactly one parameter")
    elif func_name == 'min':
        if len(params) != 1:
            raise ValueError("mode function requires exactly one parameter")
    elif func_name == 'value':
        if len(params) != 1:
            raise ValueError("average function requires exactly one parameter")
    elif func_name not in ['sum', 'average', 'sumproduct', 'count', 'unique', 'mode', 'max', 'min', 'value']:
        raise ValueError(f"Unknown function: {func_name}")
    
    evaluated_params = []
    for param in params:
        if '(' in param:
            # This is a nested function
            nested_match = re.match(r'(\w+(?:\.\w+)?)\((.*)\)', param)
            if nested_match:
                nested_func, nested_params = nested_match.groups()
                nested_result = eval_function(
                    nested_func,
                    parse_function_params(nested_params),
                    result,
                    column_list
                )
                evaluated_params.append(nested_result)
        else:
            # This is a column name
            if param not in column_list:
                raise ValueError(f"Invalid column name: {param}")
            evaluated_params.append(param)

    # Now handle the main function
    if func_name == 'sum':
        col = evaluated_params[0]
        return sum(float(row[col]) for row in result if col in row and row[col] is not None)
        
    elif func_name == 'average':
        col = evaluated_params[0]
        values = [float(row[col]) for row in result if col in row and row[col] is not None]
        return mean(values)
        
    elif func_name == 'sumproduct':
        value_col, weight_col = evaluated_params
        
        valid_pairs = [(float(row[value_col]), float(row[weight_col])) 
                     for row in result 
                     if row[value_col] is not None and row[weight_col] is not None]
        
        if not valid_pairs:
            return 0
            
        return sum(v * w for v, w in valid_pairs)
        
    elif func_name == 'count':
        col = evaluated_params[0]
        return float(len([row[col] for row in result if col in row and row[col] is not None]))
        
    elif func_name == 'unique':
        col = evaluated_params[0]
        unique_values = set(str(row[col]) for row in result if col in row and row[col] is not None)
        return ', '.join(sorted(unique_values))
        
    elif func_name == 'mode':
        col = evaluated_params[0]
        values = [str(row[col]) for row in result if col in row and row[col] is not None]
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
        col = evaluated_params[0]
        values = [row[col] for row in result if col in row and row[col] is not None]
        try:
            numeric_values = [float(val) for val in values]
            return max(numeric_values)
        except ValueError:
            return max(values)
            
    elif func_name == 'min':
        col = evaluated_params[0]
        values = [row[col] for row in result if col in row and row[col] is not None]
        try:
            numeric_values = [float(val) for val in values]
            return min(numeric_values)
        except ValueError:
            return min(values)
            
    elif func_name == 'value':
        col = evaluated_params[0]
        values = [row[col] for row in result if col in row and row[col] is not None]
        try:
            # For numeric values, try to convert to float
            numeric_values = [float(val) for val in values]
            return ', '.join(str(val) for val in numeric_values)
        except ValueError:
            # For non-numeric values, return as strings
            return ', '.join(str(val) for val in values)
    
    else:
        raise ValueError(f"Unknown function: {func_name}")

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
