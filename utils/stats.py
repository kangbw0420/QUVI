import json
import pandas as pd
from decimal import Decimal
from typing import List, Dict, Union

currency_list = [
    "AED",
    "ARS",
    "AUD",
    "BDT",
    "BHD",
    "BND",
    "BRL",
    "CAD",
    "CHF",
    "CLP",
    "CNH",
    "CNY",
    "COP",
    "CZK",
    "DKK",
    "EGP",
    "ETB",
    "EUR",
    "FJD",
    "GBP",
    "HKD",
    "HUF",
    "IDR",
    "ILS",
    "INR",
    "JOD",
    "JPY",
    "KRW",
    "KES",
    "KHR",
    "KWD",
    "KZT",
    "LKR",
    "LYD",
    "MMK",
    "MNT",
    "MOP",
    "MXN",
    "MYR",
    "NOK",
    "NPR",
    "NZD",
    "OMR",
    "PHP",
    "PKR",
    "PLN",
    "QAR",
    "RON",
    "RUB",
    "SAR",
    "SEK",
    "SGD",
    "THB",
    "TRY",
    "TWD",
    "USD",
    "UZS",
    "VND",
    "ZAR",
]

def calculate_stats(data: Union[List[Dict], Dict[str, List[Dict]]], selected_table: str) -> Union[str, List[str]]:
    """데이터프레임의 각 컬럼 타입을 자동으로 감지하여 분석합니다.
    Args:
        data: 분석할 데이터 (단일 리스트 또는 회사별 구조화된 딕셔너리)
        selected_table: 테이블 유형 ('amt' 또는 'trsc')
    Returns:
        Union[str, List[str]]: 분석 결과를 담은 문자열 또는 문자열 리스트
    """
    if isinstance(data, dict):
        # 회사별로 구조화된 데이터인 경우
        all_results = []
        for company, company_data in data.items():
            df = pd.DataFrame(company_data)
            if len(df) == 0:
                continue
                
            result_parts = []
            result_parts.append(f"\n{company} 회사의 분석 결과:")
            
            currency_column = None
                
            ### 1. column 전처리 ###
            for col in df.columns:
                # Decimal 타입을 float로 변환 / currency_column이 있는 경우
                if isinstance(df[col].dropna().iloc[0], Decimal):
                    df[col] = df[col].astype(float)
                # currency_column인지 확인
                first_three_values = df[col].head(3).astype(str).tolist()
                if all(val.upper() in currency_list for val in first_three_values):
                    currency_column = col
                    
            ### 2. column별 통계 ###
            for col in df.columns:
                ### 2-1. is_float_dtype -> currency_col이 있는 경우 currency 별로 합계 / 아니면 통 합계 ###
                if pd.api.types.is_float_dtype(df[col]):
                    if currency_column:
                        currency_stats = (
                            df.groupby(currency_column)[col]
                            .agg({"sum", "count"})
                            .reset_index()
                        )
                        
                        result_str = f"- {col}의 통화별 통계:\n"
                        for _, row in currency_stats.iterrows():
                            result_str += (
                                f"  - {row[currency_column]} 통화:\n"
                                f"    합계: {row['sum']:,.2f}\n"
                                f"    데이터 수: {row['count']:,}개\n"
                            )
                    else:
                        stats = {
                            "합계": df[col].sum(),
                            "개수": df[col].count(),
                        }
                        result_str = (
                            f"- {col}에 대한 통계:\n"
                            f"  합계: {stats['합계']:,}\n"
                            f"  데이터 수: {stats['개수']:,}개\n"
                        )
                    result_parts.append(result_str)
                ### 2-2. !is_float_dtype -> 상위 10개 ###
                else:
                    values = df[col].head(10).tolist()
                    formatted_values = [str(v) for v in values]
                    result_str = f"- {col}의 주요 값 리스트: {formatted_values}\n"
                    result_parts.append(result_str)
                    
            all_results.extend(result_parts)
        return all_results if all_results else ["데이터가 없습니다."]
        
    else:
        # 기존의 단일 리스트 처리 로직
        df = pd.DataFrame(data)
        if len(df) == 0:
            return ["데이터가 없습니다."]
            
        result_parts = []
        
        if selected_table not in ["amt", "trsc"]:
            raise ValueError(
                f"선택된 테이블({selected_table})이 유효하지 않습니다. 'amt' 또는 'trsc'만 가능합니다."
            )
   
        currency_column = None
        ### 1. column 전처리 ###
        for col in df.columns:
            # Decimal 타입을 float로 변환 / currency_column이 있는 경우
            if isinstance(df[col].dropna().iloc[0], Decimal):
                df[col] = df[col].astype(float)

            # currency_column인지 확인
            first_three_values = df[col].head(3).astype(str).tolist()
            if all(val.upper() in currency_list for val in first_three_values):
                currency_column = col
                
        ### 2. column별 통계 ###
        for col in df.columns:
            ### 2-1. is_float_dtype -> currency_col이 있는 경우 currency 별로 합계 / 아니면 통 합계 ###
            if pd.api.types.is_float_dtype(df[col]):
                if currency_column:
                    currency_stats = (
                        df.groupby(currency_column)[col]
                        .agg({"sum", "count"})
                        .reset_index()
                    )
                    
                    result_str = f"- {col}의 통화별 통계:\n"
                    for _, row in currency_stats.iterrows():
                        result_str += (
                            f"- {row[currency_column]} 통화:\n"
                            f"합계: {row['sum']:,.2f}\n"
                            f"데이터 수: {row['count']:,}개\n"
                        )
                else:
                    stats = {
                        "합계": df[col].sum(),
                        "개수": df[col].count(),
                    }
                    result_str = (
                        f"- {col}에 대한 통계:\n"
                        f"합계: {stats['합계']:,}\n"
                        f"데이터 수: {stats['개수']:,}개\n"
                    )
                result_parts.append(result_str)
            ### 2-2. !is_float_dtype -> 상위 10개 ###
            else:
                values = df[col].head(10).tolist()
                formatted_values = [str(v) for v in values]
                result_str = f"{col}의 주요 값 리스트: {formatted_values}\n"
                result_parts.append(result_str)
                
        return result_parts
    
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