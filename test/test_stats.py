import pytest
from decimal import Decimal
from utils.stats import calculate_stats

# amt 테이블 테스트 데이터
amt_test_data_1 = [
    {
        "view_dv": "전체",
        "com_nm": "웹케시",
        "bank_nm": "국민은행",
        "acct_no": "123-456-789",
        "curr_cd": "KRW",
        "acct_bal_amt": Decimal("1000000"),
        "real_amt": Decimal("900000"),
        "acct_bal_won": Decimal("1000000"),
        "reg_dt": "20240201"
    },
    {
        "view_dv": "전체",
        "com_nm": "웹케시",
        "bank_nm": "신한은행",
        "acct_no": "987-654-321",
        "curr_cd": "USD",
        "acct_bal_amt": Decimal("5000"),
        "real_amt": Decimal("4500"),
        "acct_bal_won": Decimal("6500000"),
        "reg_dt": "20240201"
    }
]

amt_test_data_2 = [
    {
        "view_dv": "증권",
        "com_nm": "웹케시",
        "bank_nm": "미래에셋증권",
        "acct_no": "111-222-333",
        "stock_nm": "삼성전자",
        "bal_qunt": Decimal("100"),
        "prchs_price": Decimal("70000"),
        "curr_amt": Decimal("75000"),
        "prchs_amt": Decimal("7000000"),
        "appr_amt": Decimal("7500000"),
        "valu_gain_loss": Decimal("500000"),
        "return_rate": Decimal("7.14"),
        "reg_dt": "20240201"
    },
    {
        "view_dv": "증권",
        "com_nm": "웹케시",
        "bank_nm": "미래에셋증권",
        "acct_no": "444-555-666",
        "stock_nm": "현대차",
        "bal_qunt": Decimal("50"),
        "prchs_price": Decimal("180000"),
        "curr_amt": Decimal("175000"),
        "prchs_amt": Decimal("9000000"),
        "appr_amt": Decimal("8750000"),
        "valu_gain_loss": Decimal("-250000"),
        "return_rate": Decimal("-2.78"),
        "reg_dt": "20240201"
    }
]

# trsc 테이블 테스트 데이터
trsc_test_data_1 = [
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
    }
]

trsc_test_data_2 = [
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
    },
    {
        "view_dv": "전체",
        "com_nm": "웹케시",
        "bank_nm": "KB증권",
        "acct_no": "777-888-999",
        "curr_cd": "USD",
        "in_out_dv": "출금",
        "trsc_amt": Decimal("2000"),
        "trsc_bal": Decimal("13000"),
        "reg_dt": "20240201",
        "trsc_tm": "143000"
    }
]

# stock 테이블 테스트 데이터
stock_test_data_1 = [
    {
        "com_nm": "웹케시",
        "bank_nm": "미래에셋증권",
        "acct_no": "111-222-333",
        "curr_cd": "KRW",
        "stock_nm": "삼성전자",
        "bal_qunt": Decimal("100"),
        "prchs_price": Decimal("70000"),
        "prchs_amt": Decimal("7000000"),
        "curr_amt": Decimal("75000"),
        "valu_gain_loss": Decimal("500000"),
        "appr_amt": Decimal("7500000"),
        "return_rate": Decimal("7.14"),
        "reg_dt": "20240201"
    },
    {
        "com_nm": "웹케시",
        "bank_nm": "미래에셋증권",
        "acct_no": "444-555-666",
        "curr_cd": "KRW",
        "stock_nm": "SK하이닉스",
        "bal_qunt": Decimal("50"),
        "prchs_price": Decimal("130000"),
        "prchs_amt": Decimal("6500000"),
        "curr_amt": Decimal("135000"),
        "valu_gain_loss": Decimal("250000"),
        "appr_amt": Decimal("6750000"),
        "return_rate": Decimal("3.85"),
        "reg_dt": "20240201"
    }
]

stock_test_data_2 = [
    {
        "com_nm": "웹케시",
        "bank_nm": "KB증권",
        "acct_no": "777-888-999",
        "curr_cd": "USD",
        "stock_nm": "APPLE",
        "bal_qunt": Decimal("10"),
        "prchs_price": Decimal("150"),
        "prchs_amt": Decimal("1500"),
        "curr_amt": Decimal("180"),
        "valu_gain_loss": Decimal("300"),
        "appr_amt": Decimal("1800"),
        "return_rate": Decimal("20"),
        "reg_dt": "20240201"
    },
    {
        "com_nm": "웹케시",
        "bank_nm": "KB증권",
        "acct_no": "777-888-999",
        "curr_cd": "USD",
        "stock_nm": "MICROSOFT",
        "bal_qunt": Decimal("5"),
        "prchs_price": Decimal("300"),
        "prchs_amt": Decimal("1500"),
        "curr_amt": Decimal("320"),
        "valu_gain_loss": Decimal("100"),
        "appr_amt": Decimal("1600"),
        "return_rate": Decimal("6.67"),
        "reg_dt": "20240201"
    }
]

def test_amt_basic():
    print("\n=== AMT 기본 계좌 테스트 ===")
    stats = calculate_stats(amt_test_data_1)
    print("\n".join(stats))
    assert len(stats) > 0
    assert any("acct_bal_amt" in s for s in stats)
    assert any("KRW" in s for s in stats)
    assert any("USD" in s for s in stats)

def test_amt_stock():
    print("\n=== AMT 증권 계좌 테스트 ===")
    stats = calculate_stats(amt_test_data_2)
    print("\n".join(stats))
    assert len(stats) > 0
    assert any("valu_gain_loss" in s for s in stats)
    assert any("return_rate" in s for s in stats)

def test_trsc_krw():
    print("\n=== TRSC KRW 거래 테스트 ===")
    stats = calculate_stats(trsc_test_data_1)
    print("\n".join(stats))
    assert len(stats) > 0
    assert any("입금" in s for s in stats)
    assert any("출금" in s for s in stats)
    assert any("1,000,000" in s for s in stats)

def test_trsc_usd():
    print("\n=== TRSC USD 거래 테스트 ===")
    stats = calculate_stats(trsc_test_data_2)
    print("\n".join(stats))
    assert len(stats) > 0
    assert any("USD" in s for s in stats)
    assert any("입금" in s for s in stats)
    assert any("출금" in s for s in stats)

def test_stock_krw():
    print("\n=== STOCK KRW 테스트 ===")
    stats = calculate_stats(stock_test_data_1)
    print("\n".join(stats))
    assert len(stats) > 0
    assert any("valu_gain_loss" in s for s in stats)
    assert any("return_rate" in s for s in stats)

def test_stock_usd():
    print("\n=== STOCK USD 테스트 ===")
    stats = calculate_stats(stock_test_data_2)
    print("\n".join(stats))
    assert len(stats) > 0
    assert any("USD" in s for s in stats)
    assert any("valu_gain_loss" in s for s in stats)
    assert any("return_rate" in s for s in stats)

def test_empty_data():
    print("\n=== 빈 데이터 테스트 ===")
    stats = calculate_stats([])
    print("\n".join(stats))
    assert stats == ["데이터가 없습니다."]