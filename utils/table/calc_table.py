from string import Formatter
import pandas as pd
from typing import List, Dict, Any

from utils.logger import setup_logger

logger = setup_logger('main_table')


def evaluate_fstring_template(fstring: str, data: List[Dict[str, Any]]) -> str:
    """f-string 응답 내 pandas 표현식 평가"""
    try:
        # 데이터가 DataFrame이라면 그대로 사용, 아니면 DataFrame으로 변환
        if isinstance(data, pd.DataFrame):
            df = data
        else:
            df = pd.DataFrame(data)

        # 💡 전처리: row 0이 dict들로 구성된 경우 → 이를 풀어서 새 DataFrame 만들기
        if df.shape[0] == 2 and all(isinstance(cell, dict) for cell in df.iloc[0]):
            raw_data = df.iloc[0]
            records = [cell for cell in raw_data if isinstance(cell, dict)]
            df = pd.DataFrame(records)

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
        # ✅ df의 컬럼들을 safe_globals에 직접 바인딩
        for col in df.columns:
            safe_globals[col] = df[col]

        # ✅ 표현식이 없거나 공백만 있는 경우 그대로 반환
        if all(not expr or not expr.strip() for _, expr, *_ in Formatter().parse(fstring)):
            return fstring

        result_parts = []
        for literal_text, expr, *_ in Formatter().parse(fstring):
            result_parts.append(literal_text)
            if expr and expr.strip():
                # 사용자 정의 표현식 치환 예시
                expr = expr.replace('count(acct_no)', 'len(df["acct_no"])')
                try:
                    evaluated = eval(expr.strip(), safe_globals, {})
                    result_parts.append(str(evaluated))
                except Exception as e:
                    return f"Error evaluating expression '{expr}': {str(e)}"

        return ''.join(result_parts)

    except Exception as e:
        return f"Error processing f-string: {str(e)}"
