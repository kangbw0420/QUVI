# 현재는 사용하지 않는 모듈. respondent가 적절한 format_spec/conversion을 생성하지 못한다면 사용될 예정
# from typing import List
# from decimal import Decimal, ROUND_HALF_UP

# .count가 있으면 정수로 표시
# STRING_COLUMN인지 확인
# DECIMAL_COLUMN은 소수점 2자리까지 표시
# 단, 컬럼이 CURRENCY_LIST인 경우 원화는 정수로 표시, 나머지 통화는 소수점 2자리까지 표시
# 나머지는 정수로 표시

CURRENCY_LIST = [
    "AED", "ARS", "AUD", "BDT", "BHD", "BND", "BRL", "CAD", "CHF", "CLP",
    "CNH", "CNY", "COP", "CZK", "DKK", "EGP", "ETB", "EUR", "FJD", "GBP",
    "HKD", "HUF", "IDR", "ILS", "INR", "JOD", "JPY", "KRW", "KES", "KHR",
    "KWD", "KZT", "LKR", "LYD", "MMK", "MNT", "MOP", "MXN", "MYR", "NOK",
    "NPR", "NZD", "OMR", "PHP", "PKR", "PLN", "QAR", "RON", "RUB", "SAR",
    "SEK", "SGD", "THB", "TRY", "TWD", "USD", "UZS", "VND", "ZAR"
]

STRING_COLUMN = {
    'note1',  # 적요
    'trsc_dv',  # 거래구분
    'bank_nm',  # 은행명
    'com_nm',   # 회사명
    'acct_no',  # 계좌번호
    'acct_dv',  # 계좌구분
    'stock_nm'  # 주식명
    'KRW_p_day',
    'p_day',
    'reg_dt',
    'trsc_dt',
    'open_dt',
    'due_dt'
}

DECIMAL_COLUMN = {'intr_rate'}

NO_DECIMAL_FUNC = {'count'}