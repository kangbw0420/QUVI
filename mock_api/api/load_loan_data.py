import pandas as pd
from typing import List, Dict, Optional
import json
from datetime import datetime


def load_loan_transaction_data(
    from_date: Optional[str] = None, to_date: Optional[str] = None
) -> Optional[List[Dict]]:
    """
    Load loan transaction data from JSON file and optionally filter by date range

    Args:
        from_date (str, optional): Start date in YYYYMMDD format. If None, no start date filter
        to_date (str, optional): End date in YYYYMMDD format. If None, no end date filter

    Returns:
        List[Dict]: Loan transaction records, filtered by date range if dates are provided
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
            "mock_api/data/loan/loan_transaction.json", "r", encoding="utf-8"
        ) as f:
            data = json.load(f)
            transactions = data.get("loan_trsc", [])

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


def load_loan_transaction_data_api(
    from_date: Optional[str] = None, to_date: Optional[str] = None
):
    """
    Mock API to load loan transaction data and convert to DataFrame with proper data types
    """
    data = load_loan_transaction_data(from_date, to_date)

    # Create DataFrame
    transactions = pd.DataFrame(data)

    # Convert data types for all loan transaction fields
    if len(transactions) > 1:
        transactions = transactions.astype(
            {
                "BANK_CD": "string",  # 은행 코드
                "ACCT_NO": "string",  # 계좌번호
                "TRSC_DT": "string",  # 거래일자
                "TRSC_SEQ_NO": "string",  # 거래 순번
                "CURR_CD": "string",  # 통화코드
                "LOAN_TRSC_DV": "string",  # 대출거래구분
                "TRSC_AMT": "float64",  # 거래금액
                "LOAN_TRSC_AMT": "float64",  # 대출거래금액
                "LOAN_BAL": "float64",  # 대출잔액
                "LOAN_RATE": "float64",  # 대출금리
                "LOAN_INTR_AMT": "float64",  # 대출이자금액
                "MNUL_WRT_YN": "string",  # 수동입력여부
                "NOTE1": "string",  # 비고
            }
        )

        # Convert date fields
        transactions["TRSC_DT"] = pd.to_datetime(
            transactions["TRSC_DT"], format="%Y%m%d"
        )

        # Handle optional date fields
        date_columns = ["LOAN_INTR_ST_DT", "LOAN_INTR_EN_DT"]
        for col in date_columns:
            if col in transactions.columns:
                transactions[col] = pd.to_datetime(
                    transactions[col], format="%Y%m%d", errors="coerce"
                )

    result = f"대출 거래 데이터 api를 성공적으로 호출, 총 {len(transactions)}개의 거래 내역을 로드했습니다."

    return result, transactions


def load_loan_balance_data_api() -> pd.DataFrame:
    """
    Load loan balance data from JSON file and convert to DataFrame with proper data types.

    Returns:
        pd.DataFrame: Loan balance data with properly typed columns
        None: If there's an error loading or processing the data
    """
    try:
        with open("mock_api/data/loan/loan_balance.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            balance_data = data.get("loan_accounts", {})

            # Convert to DataFrame
            balance = pd.DataFrame(balance_data)

            # Convert data types for all loan balance fields
            balance = balance.astype(
                {
                    "BANK_CD": "string",  # 은행코드
                    "ACCT_NO": "string",  # 계좌번호
                    "ACCT_DV": "string",  # 계좌구분
                    "CURR_CD": "string",  # 통화코드
                    "ACCT_NICK_NM": "string",  # 계좌별칭
                    "ACCT_BAL_AMT": "float64",  # 계좌잔액
                    "ACCT_BAL_WON": "float64",  # 원화잔액
                    "REAL_AMT": "float64",  # 실제금액
                    "CNTRCT_AMT": "float64",  # 계약금액
                    "INTR_RATE": "float64",  # 이자율
                    "LOAN_SBJT": "string",  # 대출과목
                    "REPAY_MTHD": "string",  # 상환방법
                    "INTR_PAY_DT": "string",  # 이자납입일
                    "TRMN_YN": "string",  # 해지여부
                }
            )

            # Convert all date type fields
            date_columns = {
                # YYYYMMDD format
                "NEW_DT": "%Y%m%d",  # 신규일자
                "DUE_DT": "%Y%m%d",  # 만기일자
                "TRMN_DT": "%Y%m%d",  # 해지일자
                "OPEN_DT": "%Y%m%d",  # 개설일자
                # YYYYMMDDHHMMSS format
                "REG_DTM": "%Y%m%d%H%M%S",  # 등록일시
                "CORC_DTM": "%Y%m%d%H%M%S",  # 수정일시
            }

            for col, date_format in date_columns.items():
                if col in balance.columns:
                    balance[col] = pd.to_datetime(
                        balance[col], format=date_format, errors="coerce"
                    )

            total_loan_amount = balance["CNTRCT_AMT"].sum()
            count_accounts = balance["ACCT_NO"].count()

            result = f"대출 잔액 데이터 api를 성공적으로 호출, 총 {count_accounts}개 계좌에서 {total_loan_amount}원의 대출 계약금이 있습니다."

            return result, balance, total_loan_amount

    except FileNotFoundError:
        print("Loan balance data file not found")
        return None
    except json.JSONDecodeError as je:
        print(f"JSON parsing error: {str(je)}")
        return None
    except Exception as e:
        print(f"Error loading loan balance data: {str(e)}")
        return None
