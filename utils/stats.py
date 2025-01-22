import pandas as pd
from decimal import Decimal
from typing import List, Dict, Any, Union

currency_list = [
    "AED", "ARS", "AUD", "BDT", "BHD", "BND", "BRL", "CAD", "CHF", "CLP",
    "CNH", "CNY", "COP", "CZK", "DKK", "EGP", "ETB", "EUR", "FJD", "GBP",
    "HKD", "HUF", "IDR", "ILS", "INR", "JOD", "JPY", "KRW", "KES", "KHR",
    "KWD", "KZT", "LKR", "LYD", "MMK", "MNT", "MOP", "MXN", "MYR", "NOK",
    "NPR", "NZD", "OMR", "PHP", "PKR", "PLN", "QAR", "RON", "RUB", "SAR",
    "SEK", "SGD", "THB", "TRY", "TWD", "USD", "UZS", "VND", "ZAR"
]

def find_currency_column(data: List[Dict[str, Any]]) -> str:
    """
    데이터에서 통화 컬럼 찾기
    """
    if not data:
        return None
        
    # 첫 번째 row의 각 컬럼을 확인
    sample_row = data[0]
    for col, val in sample_row.items():
        if str(val).upper() in currency_list:
            return col
            
    return None

def convert_decimal_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Decimal 타입의 컬럼을 float로 변환
    """
    for col in df.columns:
        if len(df[col].dropna()) > 0 and isinstance(df[col].dropna().iloc[0], Decimal):
            df[col] = df[col].astype(float)
    return df

def calculate_stats(result: List[Dict[str, Any]], selected_table: str) -> List[str]:
    """
    데이터를 분석하여 통계값 생성
    
    Args:
        result: 다음 형식의 데이터
            amt 테이블: [{'key': '회사명', 'data': [...]}]
            trsc 테이블: [{'key': ['회사명', '계좌번호'], 'data': [...]}]
        selected_table: 테이블 유형 ('amt' 또는 'trsc')
        
    Returns:
        List[str]: 분석 결과를 담은 문자열 리스트
    """
    if not result:
        return ["데이터가 없습니다."]

    all_results = []
    
    for group in result:
        key = group['key']
        data = group['data']
        
        if not data:
            continue
            
        # key가 리스트(회사명, 계좌번호)인 경우와 문자열(회사명)인 경우 처리
        if isinstance(key, list):
            company_name, account_no = key
            result_header = f"\n{company_name} 회사의 계좌번호 {account_no} 분석 결과:"
        else:
            company_name = key
            result_header = f"\n{company_name} 회사 분석 결과:"
            
        result_parts = [result_header]
        
        # DataFrame 생성 및 Decimal 처리
        df = pd.DataFrame(data)
        df = convert_decimal_values(df)
        
        # 통화 컬럼 찾기
        currency_column = find_currency_column(data)
        
        # 각 컬럼별 통계 계산
        for col in df.columns:
            if pd.api.types.is_float_dtype(df[col]):
                if currency_column:
                    # 통화별 통계
                    currency_stats = (
                        df.groupby(currency_column)[col]
                        .agg(["sum", "count"])
                        .reset_index()
                    )
                    
                    result_str = f"- {col}의 통화별 통계:\n"
                    for _, row in currency_stats.iterrows():
                        result_str += (
                            f"  - {row[currency_column]} 통화:\n"
                            f"    합계: {row['sum']:,.2f}\n"
                            f"    데이터 수: {row['count']:,}개\n"
                        )
                    result_parts.append(result_str)
                else:
                    # 통화 구분 없는 통계
                    stats = {
                        "합계": df[col].sum(),
                        "개수": df[col].count()
                    }
                    result_str = (
                        f"- {col}에 대한 통계:\n"
                        f"  합계: {stats['합계']:,}\n"
                        f"  데이터 수: {stats['개수']:,}개\n"
                    )
                    result_parts.append(result_str)
            else:
                # 숫자형이 아닌 컬럼의 상위 10개 값
                values = df[col].head(10).tolist()
                formatted_values = [str(v) for v in values]
                result_str = f"- {col}의 주요 값 리스트: {formatted_values}\n"
                result_parts.append(result_str)
        
        all_results.extend(result_parts)
    
    return all_results if all_results else ["데이터가 없습니다."]