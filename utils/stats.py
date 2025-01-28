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

def calculate_transaction_stats(df: pd.DataFrame, amount_col: str) -> Dict[str, Any]:
    """입출금 거래에 대한 통계 계산"""
    stats = {}
    
    # 입금 통계
    deposits = df[df['in_out_dv'] == '입금'][amount_col]
    if not deposits.empty:
        stats['입금'] = {
            'sum': deposits.sum(),
            'count': len(deposits)
        }
    
    # 출금 통계
    withdrawals = df[df['in_out_dv'] == '출금'][amount_col]
    if not withdrawals.empty:
        stats['출금'] = {
            'sum': withdrawals.sum(),
            'count': len(withdrawals)
        }
    
    return stats

def calculate_stats(result: List[Dict[str, Any]]) -> List[str]:
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
            
        company_name = key.get('title', '')
        result_header = f"{company_name} 회사 분석 결과:\n"
            
        result_parts = [result_header]
        
        # DataFrame 생성 및 Decimal 처리
        df = pd.DataFrame(data)
        df = convert_decimal_values(df)
        
        # 통화 컬럼 찾기
        currency_column = find_currency_column(data)
        
        # 각 컬럼별 통계 계산
        for col in df.columns:
            # in_out_dv 컬럼은 입출금 통계에 사용되므로 개별 통계에서 제외
            if col == 'in_out_dv':
                continue
                
            if pd.api.types.is_float_dtype(df[col]):
                if currency_column:
                    # amt 테이블의 통화별 통계
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
                    
                elif 'in_out_dv' in df.columns and col in ['trsc_amt']:
                    # trsc 테이블의 입출금별 통계
                    trans_stats = calculate_transaction_stats(df, col)
                    result_str = f"- {col}의 입출금별 통계:\n"
                    
                    for trans_type, stats in trans_stats.items():
                        result_str += (
                            f"  - {trans_type}:\n"
                            f"    합계: {stats['sum']:,.2f}\n"
                            f"    데이터 수: {stats['count']:,}개\n"
                        )
                    result_parts.append(result_str)
                    
                elif col != 'in_out_dv':  # 일반 숫자형 컬럼 통계
                    stats = {
                        "합계": df[col].sum(),
                        "개수": df[col].count()
                    }
                    if col != 'trsc_amt':
                        result_str = (
                            f"- {col}에 대한 통계:\n"
                            f"  합계: {stats['합계']:,}\n"
                            f"  데이터 수: {stats['개수']:,}개\n"
                        )
                        result_parts.append(result_str)
                        
            elif col not in ['in_out_dv']:  # 숫자형이 아닌 컬럼의 상위 10개 값
                values = df[col].head(10).tolist()
                formatted_values = [str(v) for v in values]
                result_str = f"- {col}의 주요 값 리스트: {formatted_values}\n"
                result_parts.append(result_str)
        
        all_results.extend(result_parts)
    
    return all_results if all_results else ["데이터가 없습니다."]