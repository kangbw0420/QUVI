import re
from typing import List, Dict, Any, Union
from statistics import mean, mode, StatisticsError

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