import pytest
from decimal import Decimal
import json
from utils.dataframe.group_acct import check_acct_no

# Raw SQL 결과 형태의 테스트 데이터
test_data = [
    {
        "view_dv": "전체",
        "com_nm": "웹케시",
        "bank_nm": "국민은행",
        "acct_no": "123-456-789",
        "curr_cd": "KRW",
        "in_out_dv": "입금",
        "trsc_amt": Decimal("1000000"),
        "trsc_bal": Decimal("5000000"),
        "reg_dt": "20240201",
        "trsc_tm": "103000"
    },
    {
        "view_dv": "전체",
        "com_nm": "웹케시",
        "bank_nm": "국민은행",
        "acct_no": "123-456-789",
        "curr_cd": "KRW",
        "in_out_dv": "출금",
        "trsc_amt": Decimal("500000"),
        "trsc_bal": Decimal("4500000"),
        "reg_dt": "20240201",
        "trsc_tm": "143000"
    },
    {
        "view_dv": "전체",
        "com_nm": "웹케시",
        "bank_nm": "KB증권",
        "acct_no": "777-888-999",
        "curr_cd": "USD",
        "in_out_dv": "입금",
        "trsc_amt": Decimal("5000"),
        "trsc_bal": Decimal("15000"),
        "reg_dt": "20240201",
        "trsc_tm": "103000"
    }
]

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super(DecimalEncoder, self).default(obj)

def print_data(data):
    print(json.dumps(data, indent=2, cls=DecimalEncoder))

def test_trsc_table():
    print("\n=== TRSC 테이블 테스트 ===")
    print("\n[입력 데이터]")
    print_data(test_data)
    
    result = check_acct_no(test_data, "trsc")
    print("\n[은행별-계좌번호별 그룹화된 결과]")
    print_data(result)
    
    # trsc 테이블에서는 은행명과 계좌번호로 그룹화
    assert len(result) == 2  # 2개의 다른 은행-계좌 조합
    for group in result:
        assert 'title' in group['key']  # 은행명이 있어야 함
        assert 'subtitle' in group['key']  # 계좌번호가 있어야 함
        assert 'acct_no' not in group['data'][0]  # acct_no가 제거되어야 함
        assert 'bank_nm' not in group['data'][0]  # bank_nm이 제거되어야 함

def test_amt_table():
    print("\n=== AMT 테이블 테스트 ===")
    print("\n[입력 데이터]")
    print_data(test_data)
    
    result = check_acct_no(test_data, "amt")
    print("\n[결과 데이터 (data 키로 감싸진 형태)]")
    print_data(result)
    
    # amt 테이블에서는 data 키로 감싸서 반환
    assert len(result) == 1
    assert 'data' in result[0]
    assert result[0]['data'] == test_data

def test_stock_table():
    print("\n=== STOCK 테이블 테스트 ===")
    print("\n[입력 데이터]")
    print_data(test_data)
    
    result = check_acct_no(test_data, "stock")
    print("\n[결과 데이터 (data 키로 감싸진 형태)]")
    print_data(result)
    
    # stock 테이블에서는 data 키로 감싸서 반환
    assert len(result) == 1
    assert 'data' in result[0]
    assert result[0]['data'] == test_data

def test_no_required_columns():
    print("\n=== 필수 컬럼 없는 데이터 테스트 ===")
    data_without_required = [{k: v for k, v in row.items() if k not in ['acct_no', 'bank_nm']} for row in test_data]
    print("\n[입력 데이터]")
    print_data(data_without_required)
    
    result = check_acct_no(data_without_required, "trsc")
    print("\n[결과 데이터 (data 키로 감싸진 형태)]")
    print_data(result)
    
    # 필수 컬럼이 없으면 data 키로 감싸서 반환
    assert len(result) == 1
    assert 'data' in result[0]
    assert result[0]['data'] == data_without_required

def test_empty_data():
    print("\n=== 빈 데이터 테스트 ===")
    print("\n[입력 데이터]")
    print_data([])
    
    result = check_acct_no([], "trsc")
    print("\n[결과 데이터]")
    print_data(result)
    
    assert result == []