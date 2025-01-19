import json
import pandas as pd
from decimal import Decimal
from typing import List, Dict


def analyze_data(data: List[Dict], selected_table: str) -> str:
    """데이터프레임의 각 컬럼 타입을 자동으로 감지하여 분석합니다.
    Args:
        data: 분석할 데이터
        selected_table: 테이블 유형 ('amt' 또는 'trsc')
    Returns:
        str: 분석 결과를 담은 문자열
    """
    # DataFrame 생성
    df = pd.DataFrame(data)
    print("$" * 80)
    print(df.columns)

    if len(df) == 0:
        return "데이터가 없습니다."

    result_parts = []

    # Decimal 타입을 float로 변환
    for col in df.columns:
        if isinstance(df[col].iloc[0] if len(df) > 0 else None, Decimal):
            df[col] = df[col].astype(float)

    # 통계를 계산할 숫자형 컬럼들
    num_columns = {
        "amt": [
            "cntrct_amt",
            "real_amt",
            "acct_bal_amt",
            "return_rate",
            "tot_asset_amt",
            "deposit_amt",
        ],
        "trsc": [
            "loan_rate",
            "trsc_amt",
            "trsc_bal",
            "loan_trsc_amt",
        ],
    }

    # 상위 10개 값을 보여줄 컬럼들
    scope_columns = {
        "amt": ["note1", "bank_nm"],
        "trsc": ["note1", "bank_nm"],
    }

    # 'select *'의 쿼리인지를 확인한다 (각각의 테이블은 칼럼이 35개, 18개인데, view_dt가 빠지는 걸 감안, 1개 적은 개수로 필터링한다.)
    if (selected_table == "amt" & len(df.columns) >= 34) | (
        selected_table == "trsc" & len(df.columns) >= 17
    ):
        # 'select *'인 경우, 정해진 칼럼들에 대해서만 통계값을 준다.
        for col in df.columns:
            # 해당 칼럼이 num_columns인 경우 합계와 개수를 준다.
            if col in num_columns[selected_table]:
                try:
                    stats = {
                        "합계": int(df[col].sum()),
                        "개수": int(df[col].count()),
                    }
                    result_str = (
                        f"{col}에 대한 통계:\n"
                        f"- 합계: {stats['합계']:,}\n"
                        f"- 데이터 수: {stats['개수']:,}개"
                    )
                    result_parts.append(result_str)
                except (TypeError, ValueError) as e:
                    raise ValueError(
                        f"Warning: Could not calculate statistics for column {col}: {str(e)}"
                    )

            # 해당 칼럼이 scope_columns인 경우 상위 10개 값을 준다.
            elif col in scope_columns[selected_table] and len(df) > 0:
                values = df[col].head(10).tolist()
                # 값들을 문자열로 변환 (scope_columns만 걸렀으므로 필요 없는 로직이긴 하지만 혹시 모르니...)
                formatted_values = [str(v) for v in values]
                result_str = f"{col}의 주요 값 리스트: {formatted_values}"
                result_parts.append(result_str)

    # 'select *'이 아닌 경우, 그러니까 select_table = "amt" | "trsc"지만 컬럼 개수가 더 적은 경우인지 확인한다..
    elif selected_table in ["amt", "trsc"]:
        # 모든 칼럼에 대해서 통계값을 준다. (Select문을 통해 칼럼 개수가 줄어들었다고 가정.)
        for col in df.columns:
            # 해당 칼럼의 type이 float인 경우 합계와 개수를 준다.
            if pd.api.types.is_float_dtype(df[col]):
                try:
                    stats = {
                        "합계": df[col].sum(),
                        "개수": df[col].count(),
                    }
                    result_str = (
                        f"{col}에 대한 통계:\n"
                        f"- 합계: {stats['합계']:,}\n"
                        f"- 데이터 수: {stats['개수']:,}개"
                    )
                    result_parts.append(result_str)
                except (TypeError, ValueError) as e:
                    raise ValueError(
                        f"Warning: Could not calculate statistics for column {col}: {str(e)}"
                    )
            # 아닌 경우 상위 10개 값을 준다.
            else:
                values = df[col].head(10).tolist()
                # 값들을 문자열로 변환 (scope_columns만 걸렀으므로 필요 없는 로직이긴 하지만 혹시 모르니...)
                formatted_values = [str(v) for v in values]
                result_str = f"{col}의 주요 값 리스트: {formatted_values}"
                result_parts.append(result_str)
    # selected_table이 "amt"나 "trsc"가 아닌 경우
    else:
        raise ValueError(
            f"선택된 테이블({selected_table})이 유효하지 않습니다. 'amt' 또는 'trsc'만 가능합니다."
        )
    return result_parts


def add_order_by(query: str, selected_table: str) -> str:
    """SQL 쿼리에 ORDER BY 절을 추가하는 함수
    Returns:
        str: ORDER BY 절이 추가된 SQL 쿼리
    """
    if not query:
        return query

    # SELECT * 쿼리인지 확인 (8번째 문자가 '*'인지 체크)
    if len(query) <= 8 or query[7] != "*":
        return query

    # 이미 ORDER BY가 있는지 확인
    if "ORDER BY" in query.upper():
        return query

    # 우선 세미콜론 제거
    query = query.strip(";")

    # 테이블별 기본 정렬 기준 설정
    default_order = {
        "amt": "ORDER BY com_nm DESC, curr_cd DESC, reg_dt DESC, acct_bal_amt DESC",  # 계좌구분 오름차순
        "trsc": "ORDER BY com_nm DESC, curr_cd DESC, trsc_dt DESC, trsc_tm DESC, seq_no DESC",  # 거래일시 내림차순
    }

    order_clause = default_order.get(selected_table, "")

    # LIMIT, UNION 위치 찾기 (대소문자 구분 없이)
    query_upper = query.upper()
    limit_pos = query_upper.find("LIMIT ")
    union_pos = query_upper.find("UNION ")

    # ORDER BY를 삽입할 위치 결정
    if limit_pos != -1 and union_pos != -1:
        # LIMIT와 UNION이 모두 있는 경우 앞쪽에 있는 것 기준
        insert_pos = min(limit_pos, union_pos)
    elif limit_pos != -1:
        # LIMIT만 있는 경우
        insert_pos = limit_pos
    elif union_pos != -1:
        # UNION만 있는 경우
        insert_pos = union_pos
    else:
        # 아무 것도 없는 경우
        insert_pos = len(query)

    # 쿼리 조립
    result = (
        query[:insert_pos].rstrip()
        + " "
        + order_clause
        + " "
        + query[insert_pos:].lstrip()
    )

    # 마지막에 세미콜론 추가
    return result + ";"


def columns_filter(query_result: list, selected_table_name: str):
    result = query_result

    with open("temp.json", "r", encoding="utf-8") as f:  # 테이블에 따른 컬럼리스트
        columns_list = json.load(f)

    # node에서 query_result 의 element 존재유무를 검사했으니 column name 기준으로 '거래내역'과 '잔액'을 구분
    if selected_table_name == "trsc":
        filtered_result = []  # 필터링한 결과를 출력할 변수
        # view_dv로 인텐트트 구분
        if "view_dv" in result[0]:
            columns_to_remove = columns_list["trsc"][result[0]["view_dv"]]
            for x in result:
                x = {k: v for k, v in x.items() if k not in columns_to_remove}
                filtered_result.append(x)
        else:  # view_dv가 없기 때문에 '전체'에 해당되는 column list만 출력
            columns_to_remove = columns_list["trsc"]["전체"]
            for x in result:
                x = {k: v for k, v in x.items() if k not in columns_to_remove}
                filtered_result.append(x)
        return filtered_result
    elif selected_table_name == "amt":
        filtered_result = []
        if "view_dv" in result[0]:
            columns_to_remove = columns_list["amt"][result[0]["view_dv"]]
            for x in result:
                x = {k: v for k, v in x.items() if k not in columns_to_remove}
                filtered_result.append(x)
        else:
            columns_to_remove = columns_list["amt"]["전체"]
            for x in result:
                x = {k: v for k, v in x.items() if k not in columns_to_remove}
                filtered_result.append(x)
        return filtered_result
    else:  # 해당사항 없으므로 본래 resul값 출력
        return result