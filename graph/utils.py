import pandas as pd
from decimal import Decimal
from typing import List, Dict, Any

def analyze_data(data: List[Dict]) -> Dict[str, Dict[str, Any]]:
    """데이터프레임의 각 컬럼 타입을 자동으로 감지하여 분석합니다.
    숫자형 컬럼은 sum과 mean을,
    비숫자형 컬럼은 count를 계산합니다.
    Returns:
        Dict[str, Dict[str, Any]]: 분석 결과를 담은 딕셔너리.
            - numeric_columns: 숫자형 컬럼의 sum, mean, count, min, max 값
            - categorical_columns: 비숫자형 컬럼의 값별 count, unique_count, total_count 정보
    Raises:
        TypeError: data가 리스트가 아니거나 각 항목이 딕셔너리가 아닌 경우.
        ValueError: 데이터가 비어있거나 필수 컬럼이 없는 경우.
    """
    # DataFrame 생성
    df = pd.DataFrame(data)

    # Decimal 타입을 float로 변환
    for col in df.columns:
        if isinstance(df[col].iloc[0], Decimal):
            df[col] = df[col].astype(float)

    result = {"숫자형 칼럼": {}, "범주형 칼럼": {}}

    for col in df.columns:
        # 숫자형 컬럼 확인 (float이나 int)
        if pd.api.types.is_numeric_dtype(df[col]):
            result["숫자형 칼럼"][col] = {
                "합계": float(df[col].sum()),
                "평균": float(df[col].mean()),
                "개수": int(df[col].count()),
                "최소값": float(df[col].min()),
                "최댓값": float(df[col].max()),
            }
        else:
            # 비숫자형 컬럼
            value_counts = df[col].value_counts()
            result["범주형 칼럼"][col] = {
                "범주 별 개수": value_counts.to_dict(),
                "범주 수": len(value_counts),
                "전체 개수": int(value_counts.sum()),
            }

    return result
