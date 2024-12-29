import re


def calculator(expression, calc_data):
    """
    Calculates the result of a mathematical expression.
    Supports basic operations (+, -, *, /, (, )), floating point numbers.

    Args:
        expression (str): The mathematical expression to evaluate

    Returns:
        float: Result of the calculation

    Raises:
        ValueError: If the expression is invalid
        ZeroDivisionError: If division by zero is attempted

    Examples:
        >>> calculate("2 + 2")
        4
        >>> calculate("(5 + 3) * 2")
        16
        >>> calculate("10 / 2 + 3")
        8.0
    """
    expression = re.sub(r"#E\d+", lambda m: str(calc_data[m.group()]), expression)
    try:
        # Remove all spaces from the expression
        expression = expression.replace(" ", "")

        # Basic security check - only allow numbers and basic operators
        allowed_chars = set("0123456789+-*/.() '\"")
        if not all(c in allowed_chars for c in expression):
            raise ValueError("Invalid characters in expression")

        # Use eval() with safe expression
        print(expression)
        result = eval(expression)

        return_string = f"요청하신 계산의 결과는 {result}입니다"

        return return_string

    except ZeroDivisionError:
        raise ZeroDivisionError("Division by zero is not allowed")
    except:
        raise ValueError("Invalid expression")
