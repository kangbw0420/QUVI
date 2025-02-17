from typing import List
from decimal import Decimal, ROUND_HALF_UP

currency_list = [
    "AED", "ARS", "AUD", "BDT", "BHD", "BND", "BRL", "CAD", "CHF", "CLP",
    "CNH", "CNY", "COP", "CZK", "DKK", "EGP", "ETB", "EUR", "FJD", "GBP",
    "HKD", "HUF", "IDR", "ILS", "INR", "JOD", "JPY", "KRW", "KES", "KHR",
    "KWD", "KZT", "LKR", "LYD", "MMK", "MNT", "MOP", "MXN", "MYR", "NOK",
    "NPR", "NZD", "OMR", "PHP", "PKR", "PLN", "QAR", "RON", "RUB", "SAR",
    "SEK", "SGD", "THB", "TRY", "TWD", "USD", "UZS", "VND", "ZAR"
]

string_columns = {
    'note1',  # 적요
    'trsc_dv',  # 거래구분
    'bank_nm',  # 은행명
    'com_nm',   # 회사명
    'acct_no',  # 계좌번호
    'acct_dv',  # 계좌구분
    'stock_nm'  # 주식명
    'KRW_p_day',
    'p_day'
}

def should_use_decimals(column: str, func_name: str, params: List[str] = None) -> bool:
    """Determine if a column should use decimal places in its formatting"""
    no_decimal_funcs = {'count'}
    if func_name in no_decimal_funcs:
        return False

    must_decimal_column = {'intr_rate'}

    if params:
        for param in params:
            if param in must_decimal_column:
                return True
            for curr in currency_list:
                if curr != 'KRW' and param.startswith(f"{curr}_"):
                    return True

    if column in must_decimal_column:
        return True
        
    for curr in currency_list:
        if curr != 'KRW' and column.startswith(f"{curr}_"):
            return True
            
    return False

def format_number(value: float, column: str, func_name: str = '', params: List[str] = None) -> str:
    """Format a number according to the column and function rules"""
    try:
        # 문자열 컬럼 체크를 먼저 수행
        if column in string_columns:
            return str(value)
            
        if func_name in ['count']:
            return format(int(value), ',')

        # Decimal 타입 유지
        decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
        
        if should_use_decimals(column, func_name, params):
            # 소수점 2자리까지
            formatted = decimal_value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        else:
            # 정수로
            formatted = decimal_value.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            
        return format(formatted, ',')
        
    except (ValueError, TypeError):
        return str(value)