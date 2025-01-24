import pytest
from decimal import Decimal
from utils.check_com import check_com_nm
from utils.check_acct import check_acct_no
from utils.stats import calculate_stats

# amt 테이블 테스트 케이스
amt_case1 = {
    "description": "단일 회사, 단일 통화",
    "input": [
        {
            "com_nm": "쿠콘",
            "curr_cd": "KRW",
            "acct_bal_amt": Decimal("1000000.00")
        },
        {
            "com_nm": "쿠콘",
            "curr_cd": "KRW",
            "acct_bal_amt": Decimal("2000000.00")
        }
    ]
}

amt_case2 = {
    "description": "단일 회사, 다중 통화",
    "input": [
        {
            "com_nm": "쿠콘",
            "curr_cd": "KRW",
            "acct_bal_amt": Decimal("1000000.00")
        },
        {
            "com_nm": "쿠콘",
            "curr_cd": "USD",
            "acct_bal_amt": Decimal("2000000.00")
        }
    ]
}

amt_case3 = {
    "description": "다중 회사, 다중 통화",
    "input": [
        {
            "com_nm": "쿠콘",
            "curr_cd": "KRW",
            "acct_bal_amt": Decimal("1000000.00")
        },
        {
            "com_nm": "쿠콘",
            "curr_cd": "USD",
            "acct_bal_amt": Decimal("2000000.00")
        },
        {
            "com_nm": "웹케시",
            "curr_cd": "KRW",
            "acct_bal_amt": Decimal("3000000.00")
        },
        {
            "com_nm": "웹케시",
            "curr_cd": "USD",
            "acct_bal_amt": Decimal("4000000.00")
        }
    ]
}

# trsc 테이블 테스트 케이스
trsc_case1 = {
    "description": "단일 회사, 단일 계좌, 단일 통화",
    "input": [
        {
            "com_nm": "쿠콘",
            "acct_no": "1111-111-111111",
            "curr_cd": "KRW",
            "trsc_amt": Decimal("1000000.00")
        },
        {
            "com_nm": "쿠콘",
            "acct_no": "1111-111-111111",
            "curr_cd": "KRW",
            "trsc_amt": Decimal("2000000.00")
        }
    ]
}

trsc_case2 = {
    "description": "단일 회사, 다중 계좌, 다중 통화",
    "input": [
        {
            "com_nm": "쿠콘",
            "acct_no": "1111-111-111111",
            "curr_cd": "KRW",
            "trsc_amt": Decimal("1000000.00")
        },
        {
            "com_nm": "쿠콘",
            "acct_no": "2222-222-222222",
            "curr_cd": "USD",
            "trsc_amt": Decimal("2000000.00")
        }
    ]
}

trsc_case3 = {
    "description": "다중 회사, 다중 계좌, 다중 통화",
    "input": [
        {
            "com_nm": "쿠콘",
            "acct_no": "1111-111-111111",
            "curr_cd": "KRW",
            "trsc_amt": Decimal("1000000.00")
        },
        {
            "com_nm": "쿠콘",
            "acct_no": "2222-222-222222",
            "curr_cd": "USD",
            "trsc_amt": Decimal("2000000.00")
        },
        {
            "com_nm": "웹케시",
            "acct_no": "3333-333-333333",
            "curr_cd": "KRW",
            "trsc_amt": Decimal("3000000.00")
        },
        {
            "com_nm": "웹케시",
            "acct_no": "4444-444-444444",
            "curr_cd": "USD",
            "trsc_amt": Decimal("4000000.00")
        }
    ]
}

def process_test_case(test_case, table_type):
    """테스트 케이스 처리 및 결과 출력"""
    print(f"\n{'='*50}")
    print(f"테스트 케이스: {test_case['description']}")
    print(f"{'='*50}")
    
    print("\n1. 초기 데이터:")
    print(test_case['input'])
    
    print("\n2. check_com_nm 결과:")
    com_result = check_com_nm(test_case['input'])
    print(com_result)
    
    print("\n3. calculate_stats 결과:")
    stats_result = calculate_stats(com_result)
    print(stats_result)
    
    print("\n4. check_acct_no 결과 (trsc 테이블만):")
    final_result = check_acct_no(com_result, table_type)
    print(final_result)
    
    print("\n")
    input("Enter를 눌러 다음 테스트 케이스로 진행...")

def run_tests():
    """모든 테스트 케이스 실행"""
    
    print("\nAMT 테이블 테스트 시작")
    process_test_case(amt_case1, 'amt')
    process_test_case(amt_case2, 'amt')
    process_test_case(amt_case3, 'amt')
    
    print("\nTRSC 테이블 테스트 시작")
    process_test_case(trsc_case1, 'trsc')
    process_test_case(trsc_case2, 'trsc')
    process_test_case(trsc_case3, 'trsc')

if __name__ == "__main__":
    run_tests()