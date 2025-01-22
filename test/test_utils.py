# python -m test.test_utils

import pandas as pd
from typing import Dict, List, Any
from decimal import Decimal

from utils.check_com import check_com_nm
from utils.stats import calculate_stats
from utils.filter import columns_filter

# Test datasets
test_data = {
    # AMT 테이블 테스트 케이스 1: 다중 회사, 다중 통화, 다중 view_dv
    "amt_case1": [
        {"com_nm": "삼성전자", "curr_cd": "USD", "reg_dt": "20240120", "acct_bal_amt": Decimal("1000000.00"), "view_dv": "전체"},
        {"com_nm": "삼성전자", "curr_cd": "EUR", "reg_dt": "20240120", "acct_bal_amt": Decimal("850000.00"), "view_dv": "전체"},
        {"com_nm": "삼성전자", "curr_cd": "JPY", "reg_dt": "20240120", "acct_bal_amt": Decimal("120000000.00"), "view_dv": "전체"},
        {"com_nm": "LG전자", "curr_cd": "USD", "reg_dt": "20240120", "acct_bal_amt": Decimal("750000.00"), "view_dv": "대출"},
        {"com_nm": "LG전자", "curr_cd": "CNY", "reg_dt": "20240120", "acct_bal_amt": Decimal("5000000.00"), "view_dv": "대출"},
        {"com_nm": "SK하이닉스", "curr_cd": "USD", "reg_dt": "20240120", "acct_bal_amt": Decimal("1200000.00"), "view_dv": "예적금"},
        {"com_nm": "SK하이닉스", "curr_cd": "EUR", "reg_dt": "20240120", "acct_bal_amt": Decimal("950000.00"), "view_dv": "예적금"}
    ],

    # AMT 테이블 테스트 케이스 2: 시간대별 잔액 변동
    "amt_case2": [
        {"com_nm": "현대자동차", "curr_cd": "USD", "reg_dt": "20240120", "acct_bal_amt": Decimal("2000000.00"), "view_dv": "전체"},
        {"com_nm": "현대자동차", "curr_cd": "EUR", "reg_dt": "20240120", "acct_bal_amt": Decimal("1500000.00"), "view_dv": "전체"},
        {"com_nm": "기아", "curr_cd": "USD", "reg_dt": "20240120", "acct_bal_amt": Decimal("800000.00"), "view_dv": "대출"},
        {"com_nm": "기아", "curr_cd": "JPY", "reg_dt": "20240120", "acct_bal_amt": Decimal("95000000.00"), "view_dv": "대출"},
        {"com_nm": "포스코", "curr_cd": "CNY", "reg_dt": "20240120", "acct_bal_amt": Decimal("7000000.00"), "view_dv": "예적금"},
        {"com_nm": "포스코", "curr_cd": "USD", "reg_dt": "20240120", "acct_bal_amt": Decimal("1100000.00"), "view_dv": "예적금"},
        {"com_nm": "포스코", "curr_cd": "EUR", "reg_dt": "20240120", "acct_bal_amt": Decimal("900000.00"), "view_dv": "예적금"}
    ],

    # AMT 테이블 테스트 케이스 3: 대규모 금액과 소규모 금액 혼합
    "amt_case3": [
        {"com_nm": "삼성SDI", "curr_cd": "USD", "reg_dt": "20240120", "acct_bal_amt": Decimal("5000000.00"), "view_dv": "전체"},
        {"com_nm": "삼성SDI", "curr_cd": "EUR", "reg_dt": "20240120", "acct_bal_amt": Decimal("4200000.00"), "view_dv": "전체"},
        {"com_nm": "현대모비스", "curr_cd": "JPY", "reg_dt": "20240120", "acct_bal_amt": Decimal("250000000.00"), "view_dv": "대출"},
        {"com_nm": "현대모비스", "curr_cd": "USD", "reg_dt": "20240120", "acct_bal_amt": Decimal("2300000.00"), "view_dv": "대출"},
        {"com_nm": "SK이노베이션", "curr_cd": "CNY", "reg_dt": "20240120", "acct_bal_amt": Decimal("15000000.00"), "view_dv": "예적금"},
        {"com_nm": "SK이노베이션", "curr_cd": "USD", "reg_dt": "20240120", "acct_bal_amt": Decimal("1800000.00"), "view_dv": "예적금"}
    ],

    # TRSC 테이블 테스트 케이스 1: 시간순 다중 거래
    "trsc_case1": [
        {"com_nm": "SK하이닉스", "curr_cd": "USD", "trsc_dt": "20240120", "trsc_tm": "093000", "trsc_amt": Decimal("500000.00"), "view_dv": "전체"},
        {"com_nm": "SK하이닉스", "curr_cd": "EUR", "trsc_dt": "20240120", "trsc_tm": "093500", "trsc_amt": Decimal("450000.00"), "view_dv": "전체"},
        {"com_nm": "LG화학", "curr_cd": "CNY", "trsc_dt": "20240120", "trsc_tm": "094000", "trsc_amt": Decimal("3000000.00"), "view_dv": "전체"},
        {"com_nm": "LG화학", "curr_cd": "JPY", "trsc_dt": "20240120", "trsc_tm": "094500", "trsc_amt": Decimal("45000000.00"), "view_dv": "전체"},
        {"com_nm": "포스코케미칼", "curr_cd": "USD", "trsc_dt": "20240120", "trsc_tm": "095000", "trsc_amt": Decimal("350000.00"), "view_dv": "전체"},
        {"com_nm": "포스코케미칼", "curr_cd": "EUR", "trsc_dt": "20240120", "trsc_tm": "095500", "trsc_amt": Decimal("280000.00"), "view_dv": "전체"}
    ],

    # TRSC 테이블 테스트 케이스 2: 대규모/소규모 거래 혼합
    "trsc_case2": [
        {"com_nm": "현대중공업", "curr_cd": "USD", "trsc_dt": "20240120", "trsc_tm": "100000", "trsc_amt": Decimal("1500000.00"), "view_dv": "전체"},
        {"com_nm": "현대중공업", "curr_cd": "EUR", "trsc_dt": "20240120", "trsc_tm": "100500", "trsc_amt": Decimal("1200000.00"), "view_dv": "전체"},
        {"com_nm": "삼성바이오로직스", "curr_cd": "USD", "trsc_dt": "20240120", "trsc_tm": "101000", "trsc_amt": Decimal("2500000.00"), "view_dv": "전체"},
        {"com_nm": "삼성바이오로직스", "curr_cd": "JPY", "trsc_dt": "20240120", "trsc_tm": "101500", "trsc_amt": Decimal("180000000.00"), "view_dv": "전체"},
        {"com_nm": "LG에너지솔루션", "curr_cd": "CNY", "trsc_dt": "20240120", "trsc_tm": "102000", "trsc_amt": Decimal("8000000.00"), "view_dv": "전체"}
    ],

    # TRSC 테이블 테스트 케이스 3: 빈번한 거래
    "trsc_case3": [
        {"com_nm": "카카오", "curr_cd": "USD", "trsc_dt": "20240120", "trsc_tm": "103000", "trsc_amt": Decimal("300000.00"), "view_dv": "전체"},
        {"com_nm": "카카오", "curr_cd": "JPY", "trsc_dt": "20240120", "trsc_tm": "103500", "trsc_amt": Decimal("25000000.00"), "view_dv": "전체"},
        {"com_nm": "네이버", "curr_cd": "USD", "trsc_dt": "20240120", "trsc_tm": "104000", "trsc_amt": Decimal("450000.00"), "view_dv": "전체"},
        {"com_nm": "네이버", "curr_cd": "EUR", "trsc_dt": "20240120", "trsc_tm": "104500", "trsc_amt": Decimal("380000.00"), "view_dv": "전체"},
        {"com_nm": "넷마블", "curr_cd": "USD", "trsc_dt": "20240120", "trsc_tm": "105000", "trsc_amt": Decimal("150000.00"), "view_dv": "전체"},
        {"com_nm": "넷마블", "curr_cd": "CNY", "trsc_dt": "20240120", "trsc_tm": "105500", "trsc_amt": Decimal("1000000.00"), "view_dv": "전체"}
    ]
}

def process_and_print_results(case_name: str, data: List[Dict[str, Any]], table_type: str):
    """Process a test case through the pipeline and print results"""
    print(f"\n{'='*20} Processing {case_name} {'='*20}")
    
    print("\n### Original Data ###")
    print(pd.DataFrame(data).to_string())
    
    print("\n## After check_com_nm ##")
    com_nm_result = check_com_nm(data)
    if isinstance(com_nm_result, dict):
        for company, company_data in com_nm_result.items():
            print(f"\n{company}:")
            print(pd.DataFrame(company_data).to_string())
    else:
        print(pd.DataFrame(com_nm_result).to_string())
    
    print("\n#######  After calculate_stats  #######")
    stats_result = calculate_stats(com_nm_result, table_type)
    print("\n".join(stats_result) if isinstance(stats_result, list) else stats_result)
    
    print("\n## After columns_filter ##")
    filtered_result = columns_filter(com_nm_result, table_type)
    if isinstance(filtered_result, dict):
        for company, company_data in filtered_result.items():
            print(f"\n{company}:")
            print(pd.DataFrame(company_data).to_string())
    else:
        print(pd.DataFrame(filtered_result).to_string())

def run_tests():
    """Run all test cases with user interaction"""
    test_cases = [
        ("amt_case1", "amt"),
        ("amt_case2", "amt"),
        ("amt_case3", "amt"),
        ("trsc_case1", "trsc"),
        ("trsc_case2", "trsc"),
        ("trsc_case3", "trsc")
    ]
    
    for case_name, table_type in test_cases:
        input("\nPress Enter to see next test case...")
        process_and_print_results(case_name, test_data[case_name], table_type)

if __name__ == "__main__":
    run_tests()