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
    """데이터에서 통화 컬럼 찾기
    첫 행의 각 컬럼을 확인해 통화 리스트에 있는 값을 포함하는 컬럼명을 반환"""
    if not data:
        return None
        
    # 첫 번째 row의 각 컬럼을 확인
    sample_row = data[0]
    for col, val in sample_row.items():
        if str(val).upper() in currency_list:
            return col
            
    return None

def convert_decimal_values(df: pd.DataFrame) -> pd.DataFrame:
    """Decimal 타입의 컬럼을 float로 변환"""
    for col in df.columns:
        if len(df[col].dropna()) > 0 and isinstance(df[col].dropna().iloc[0], Decimal):
            df[col] = df[col].astype(float)
    return df

def calculate_transaction_stats(df: pd.DataFrame, amount_col: str, currency_col: str = None) -> Dict[str, Any]:
    """입출금 거래의 통계 계산. 통화 컬럼이 있는 경우 통화별로 그룹화하여 입출금 통계 산출
    Args:
        currency_col: None이면 통화 구분 없이 계산, str이면 해당 컬럼으로 통화별 그룹화
    Returns:
        통화코드 또는 입출금구분을 key로 하는 통계 dictionary
    """
    stats = {}
    
    # 통화별로 그룹화할지 결정
    if currency_col:
        for curr in df[currency_col].unique():
            curr_df = df[df[currency_col] == curr]
            
            # 입금 통계
            deposits = curr_df[curr_df['in_out_dv'] == '입금'][amount_col]
            if not deposits.empty:
                if curr not in stats:
                    stats[curr] = {}
                stats[curr]['입금'] = {
                    'sum': deposits.sum(),
                    'count': len(deposits)
                }
            
            # 출금 통계
            withdrawals = curr_df[curr_df['in_out_dv'] == '출금'][amount_col]
            if not withdrawals.empty:
                if curr not in stats:
                    stats[curr] = {}
                stats[curr]['출금'] = {
                    'sum': withdrawals.sum(),
                    'count': len(withdrawals)
                }
    else:
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

def format_transaction_stats(stats: Dict[str, Any], col: str) -> str:
    """거래 통계를 문자열로 포맷팅"""
    result_str = f"- {col}의 통화별 통계:\n"
    
    for curr, curr_stats in stats.items():
        result_str += f"  - {curr} 통화:\n"
        for trans_type, type_stats in curr_stats.items():
            result_str += (
                f"    {trans_type}:\n"
                f"      합계: {type_stats['sum']:,.2f}\n"
                f"      데이터 수: {type_stats['count']:,}개\n"
            )
    
    return result_str

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
                # 입출금 및 통화 모두 있는 경우
                if currency_column and 'in_out_dv' in df.columns and col in ['trsc_amt']:
                    trans_stats = calculate_transaction_stats(df, col, currency_column)
                    result_str = format_transaction_stats(trans_stats, col)
                    result_parts.append(result_str)
                
                # 통화만 있는 경우 (입출금 구분 없음)
                elif currency_column and col not in ['trsc_amt']:
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
                    
                # 입출금만 있는 경우 (통화 구분 없음)
                elif 'in_out_dv' in df.columns and col in ['trsc_amt']:
                    trans_stats = calculate_transaction_stats(df, col)
                    result_str = f"- {col}의 입출금별 통계:\n"
                    
                    for trans_type, stats in trans_stats.items():
                        result_str += (
                            f"  - {trans_type}:\n"
                            f"    합계: {stats['sum']:,.2f}\n"
                            f"    데이터 수: {stats['count']:,}개\n"
                        )
                    result_parts.append(result_str)
                    
                # 일반 숫자형 컬럼 통계
                elif col not in ['trsc_amt']:
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
                        
            elif col not in ['in_out_dv']:  # 숫자형이 아닌 컬럼의 상위 10개 값
                values = df[col].head(10).tolist()
                formatted_values = [str(v) for v in values]
                result_str = f"- {col}의 주요 값 리스트: {formatted_values}\n"
                result_parts.append(result_str)
        
        all_results.extend(result_parts)
    
    return all_results if all_results else ["데이터가 없습니다."]