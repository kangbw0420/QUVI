import pandas as pd
import re
from typing import List, Dict, Any

from utils.logger import setup_logger

logger = setup_logger('main_table')

def evaluate_pandas_expression(expr: str, data: List[Dict[str, Any]]) -> Any:
    """단일 pandas 표현식 평가"""
    try:
        df = pd.DataFrame(data)
        safe_globals = {"df": df, "pd": pd, "__builtins__": {}}
        return eval(expr, safe_globals, {})
    except Exception as e:
        return f"Error evaluating pandas expression: {str(e)}"

from string import Formatter


def evaluate_fstring_template(fstring: str, data: List[Dict[str, Any]]) -> str:
    """f-string 응답 내 pandas 표현식 평가"""
    try:
        df = pd.DataFrame(data)
        safe_globals = {
            "df": df,
            "pd": pd,
            "list": list,
            "len": len,
            "sum": sum,
            "str": str,
            "int": int,
            "float": float,
            "round": round,
            "__builtins__": {},
        }

        # ✅ 표현식이 없거나 공백만 있는 경우 그대로 반환
        if all(not expr or not expr.strip() for _, expr, *_ in Formatter().parse(fstring)):
            return fstring

        result_parts = []
        for literal_text, expr, *_ in Formatter().parse(fstring):
            result_parts.append(literal_text)
            if expr and expr.strip():
                try:
                    evaluated = eval(expr.strip(), safe_globals, {})
                    result_parts.append(str(evaluated))
                except Exception as e:
                    return f"Error evaluating expression '{expr}': {str(e)}"

        return ''.join(result_parts)

    except Exception as e:
        return f"Error processing f-string: {str(e)}"
