import pandas as pd
from typing import List, Dict, Optional
import json
from datetime import datetime


# json 거래 데이터 적재
def load_transaction_data(
    from_date: Optional[str] = None, to_date: Optional[str] = None
) -> Optional[List[Dict]]:
    """
    Load transaction data from JSON file and optionally filter by date range

    Args:
        from_date (str, optional): Start date in YYYYMMDD format. If None, no start date filter
        to_date (str, optional): End date in YYYYMMDD format. If None, no end date filter

    Returns:
        List[Dict]: Transaction records, filtered by date range if dates are provided
        None: If there's an error loading or processing the data
    """
    try:
        # Validate date format if dates are provided
        if from_date:
            datetime.strptime(from_date, "%Y%m%d")
        if to_date:
            datetime.strptime(to_date, "%Y%m%d")

        # Ensure from_date is not later than to_date if both are provided
        if from_date and to_date and from_date > to_date:
            raise ValueError("from_date cannot be later than to_date")

        with open(
            "mock_api/data/cash/webcash_transaction.json", "r", encoding="utf-8"
        ) as f:
            data = json.load(f)
            transactions = data.get("ACCT_REC", [])

            # If no dates provided, return all transactions
            if not from_date and not to_date:
                return transactions

            # Filter transactions within date range
            filtered_transactions = transactions

            if from_date:
                filtered_transactions = [
                    trans
                    for trans in filtered_transactions
                    if trans.get("TRSC_DT", "00000000") >= from_date
                ]
            if to_date:
                filtered_transactions = [
                    trans
                    for trans in filtered_transactions
                    if trans.get("TRSC_DT", "00000000") <= to_date
                ]

            return filtered_transactions

    except ValueError as ve:
        print(f"Date format error: {str(ve)}")
        return None
    except json.JSONDecodeError as je:
        print(f"JSON parsing error: {str(je)}")
        return None
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return None


# 거래 데이터 조회 mock api
def load_transaction_data_api(
    from_date: Optional[str] = None, to_date: Optional[str] = None
):
    data = load_transaction_data(from_date, to_date)

    # 데이터가 없을 때는 기본 컬럼을 가진 빈 DataFrame 반환
    if not data:
        columns = ['TRSC_TM', 'BANK_NM', 'TRSC_AMT', 'TRSC_DT', 
                  'ACCT_NO', 'TRSC_BAL', 'IN_OUT_DV', 'NOTE1']
        return "거래 데이터 api를 성공적으로 호출, 총 0개의 거래 내역을 로드했습니다.", pd.DataFrame(columns=columns)

    # 먼저 DataFrame 생성
    transactions = pd.DataFrame(data)

    # 각 컬럼의 데이터 타입 변환
    if len(transactions) > 1:
        transactions = transactions.astype(
            {
                "TRSC_TM": "int32",  # 거래시각 (정수)
                "BANK_NM": "string",  # 거래은행 (문자열)
                "TRSC_AMT": "float64",  # 거래금액 (소수점 포함)
                "TRSC_DT": "string",  # 거래일자 (YYYYMMDD 형식)
                "ACCT_NO": "string",  # 계좌번호 (문자열)
                "TRSC_BAL": "float64",  # 거래 후 잔액 (소수점 포함)
                "IN_OUT_DV": "int8",  # 입출금구분 (1 또는 2)
                "NOTE1": "string",  # 거래메모 (문자열)
            }
        )
        transactions["TRSC_DT"] = pd.to_datetime(
            transactions["TRSC_DT"], format="%Y-%m-%d"
        )
    result = f"거래 데이터 api를 성공적으로 호출, 총 {len(transactions)}개의 거래 내역을 로드했습니다."

    return result, transactions


# 잔액 데이터 조회 mock api
def load_balance_data_api() -> pd.DataFrame:
    """
    Load balance data from JSON file and convert to DataFrame with proper data types.

    Returns:
        pd.DataFrame: Balance data with properly typed columns
        None: If there's an error loading or processing the data
    """
    try:
        with open(
            "mock_api/data/cash/webcash_balance.json", "r", encoding="utf-8"
        ) as f:
            data = json.load(f)
            balance_data = data.get("DATA_REC", {}).get("ACCT_REC", [])

            # Convert to DataFrame
            balance = pd.DataFrame(balance_data)

            # Convert data types
            balance = balance.astype(
                {
                    "REAL_AMT": "float64",  # 실제 금액
                    "BANK_NM": "string",  # 은행명
                    "ACCT_BAL_AMT": "float64",  # 계좌 잔액
                    "ACCT_NO": "string",  # 계좌번호
                    "ACCT_DV_NM": "string",  # 계좌 구분명
                }
            )

            # Handle TRAN_DATE if needed (currently empty in the data)
            if "TRAN_DATE" in balance.columns:
                balance["TRAN_DATE"] = pd.to_datetime(
                    balance["TRAN_DATE"], format="%Y%m%d", errors="coerce"
                )

            sum_REAL_AMT = balance["REAL_AMT"].sum()
            count_ACCT = balance["ACCT_NO"].count()

            result = f"잔액 데이터 api를 성공적으로 호출, 총 {count_ACCT}개 계좌에서 {sum_REAL_AMT}원의 잔액이 있습니다."

            return result, balance, sum_REAL_AMT

    except FileNotFoundError:
        print("Balance data file not found")
        return None
    except json.JSONDecodeError as je:
        print(f"JSON parsing error: {str(je)}")
        return None
    except Exception as e:
        print(f"Error loading balance data: {str(e)}")
        return None


# 과거 잔액 데이터 조회 mock api
def load_past_balance_data_api(date) -> pd.DataFrame:
    """
    Load balance data from JSON file and convert to DataFrame with proper data types.

    Returns:
        pd.DataFrame: Balance data with properly typed columns
        None: If there's an error loading or processing the data
    """
    try:
        with open("mock_api/data/cash/webcash_past_balance.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            balance_data = data.get("DATA_REC", {}).get("ACCT_REC", [])

            # Convert to DataFrame
            balance = pd.DataFrame(balance_data)

            # Convert data types
            balance = balance.astype(
                {
                    "ACCT_BAL_AMT": "float64",  # 계좌 잔액
                    "ACCT_NO": "string",  # 계좌번호
                }
            )

            # Handle TRAN_DATE if needed
            if "REG_DT" in balance.columns:
                balance["REG_DT"] = pd.to_datetime(
                    balance["REG_DT"], format="%Y%m%d", errors="coerce"
                )

            # 필터링
            date_filter = pd.to_datetime(date, format="%Y%m%d")
            balance = balance[balance["REG_DT"] == date_filter]

            sum_REAL_AMT = balance["ACCT_BAL_AMT"].sum()
            count_ACCT = balance["ACCT_NO"].count()

            result = f"잔액 데이터 api를 성공적으로 호출, 총 {count_ACCT}개 계좌에서 {sum_REAL_AMT}원의 잔액이 있습니다."

            return result, balance, sum_REAL_AMT

    except FileNotFoundError:
        print("Past balance data file not found")
        return "데이터 파일을 찾을 수 없습니다.", pd.DataFrame(), 0
    except json.JSONDecodeError as je:
        print(f"JSON parsing error: {str(je)}")
        return f"데이터 파싱 오류: {str(je)}", pd.DataFrame(), 0
    except Exception as e:
        print(f"Error loading balance data: {str(e)}")
        return f"데이터 로딩 오류: {str(e)}", pd.DataFrame(), 0
