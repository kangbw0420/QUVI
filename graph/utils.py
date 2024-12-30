from pathlib import Path
import json
from typing import Union, List, Dict, Any
import pandas as pd
from decimal import Decimal


def load_prompt(prompt_path: str) -> Union[str, dict]:
    """
    입력된 경로에 존재하는 프롬프트 파일을 로드합니다.
    파일 확장자가 .json인 경우 JSON으로 파싱하여 반환하고,
    그 외의 경우 문자열로 반환합니다.

    Args:
        prompt_path (str): 프롬프트 파일의 경로.

    Returns:
        Union[str, dict]: JSON 파일인 경우 파싱된 딕셔너리, 그 외의 경우 문자열.
    """
    file_path = Path(prompt_path)

    with open(file_path, "r", encoding="utf-8") as f:
        if file_path.suffix.lower() == ".json":
            return json.load(f)
        return f.read()


def analyze_data(data: List[Dict]) -> Dict[str, Dict[str, Any]]:
    """
    데이터프레임의 각 컬럼 타입을 자동으로 감지하여 분석합니다.
    숫자형 컬럼은 sum과 mean을,
    비숫자형 컬럼은 count를 계산합니다.

    Args:
        data: 분석할 데이터 리스트

    Returns:
        컬럼별 분석 결과를 담은 딕셔너리
    """
    # DataFrame 생성
    df = pd.DataFrame(data)

    # Decimal 타입을 float로 변환
    for col in df.columns:
        if isinstance(df[col].iloc[0], Decimal):
            df[col] = df[col].astype(float)

    result = {"numeric_columns": {}, "categorical_columns": {}}

    for col in df.columns:
        # 숫자형 컬럼 확인 (float이나 int)
        if pd.api.types.is_numeric_dtype(df[col]):
            result["numeric_columns"][col] = {
                "sum": float(df[col].sum()),
                "mean": float(df[col].mean()),
                "count": int(df[col].count()),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
            }
        else:
            # 비숫자형 컬럼
            value_counts = df[col].value_counts()
            result["categorical_columns"][col] = {
                "counts": value_counts.to_dict(),
                "unique_count": len(value_counts),
                "total_count": int(value_counts.sum()),
            }

    return result
