import sys
import os
import pytest
from datetime import datetime
from typing import Tuple, Dict

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.query.view.view_table import view_table

# Test fixture for common setup
@pytest.fixture
def test_params():
    """Fixture to provide common test parameters"""
    return {
        "selected_table": "amt",
        "main_com": "Test Company",
        "user_info": ("testuser", "1234567890"),
        "flags": {
            "is_joy": False,
            "no_data": False,
            "stock_sec": False,
            "future_date": False,
            "past_date": False
        }
    }

def check_date_format(date_str):
    """Check if a date string is in YYYYMMDD format"""
    return len(date_str) == 8 and date_str.isdigit()

class TestViewTable:
    """Test cases for view_table function focusing on the date tuple format"""

    def test_single_table_query_with_future_date(self, test_params):
        """Test simple query with future date"""
        query = """
            SELECT bank_nm, acct_dv, acct_no, acct_bal_amt, real_amt, acct_bal_upd_dtm 
            FROM aicfo_get_all_amt 
            WHERE view_dv = '수시' AND curr_cd = 'KRW' AND reg_dt = '20250222'
        """
        
        # Run view_table
        transformed_query, date_ranges = view_table(
            query,
            test_params["selected_table"], 
            test_params["main_com"], 
            test_params["user_info"], 
            test_params["flags"]
        )
        
        # Check format of date_ranges
        print(f"\nTest single_table_query_with_future_date:")
        print(f"- transformed_query type: {type(transformed_query)}")
        print(f"- date_ranges type: {type(date_ranges)}")
        print(f"- date_ranges content: {date_ranges}")
        
        # Extract main date tuple
        main_date_tuple = date_ranges.get("main", date_ranges.get(next(iter(date_ranges)), None))
        
        # Validate tuple format
        assert main_date_tuple is not None, "Should have a date tuple"
        assert isinstance(main_date_tuple, tuple), "Date range should be a tuple"
        assert len(main_date_tuple) == 2, "Date tuple should have exactly 2 elements"
        
        from_date, to_date = main_date_tuple
        assert check_date_format(from_date), f"From date '{from_date}' is not in YYYYMMDD format"
        assert check_date_format(to_date), f"To date '{to_date}' is not in YYYYMMDD format"
        
        # Check future date handling
        today = datetime.now().strftime("%Y%m%d")
        assert from_date <= today, f"From date '{from_date}' should be adjusted to not exceed today '{today}'"
        assert to_date <= today, f"To date '{to_date}' should be adjusted to not exceed today '{today}'"
        assert test_params["flags"]["future_date"], "Future date flag should be set"

    def test_query_with_subquery(self, test_params):
        """Test query containing a subquery"""
        query = """
            SELECT bank_nm, acct_dv, acct_no, acct_bal_amt, real_amt, acct_bal_upd_dtm 
            FROM aicfo_get_all_amt 
            WHERE view_dv = '수시' AND curr_cd = 'KRW' AND reg_dt = '20240222' 
            AND acct_no NOT IN (
                SELECT DISTINCT acct_no 
                FROM aicfo_get_all_trsc 
                WHERE view_dv = '수시' AND curr_cd = 'KRW' AND trsc_dt > '20241121'
            )
        """
        
        # Run view_table
        transformed_query, date_ranges = view_table(
            query,
            test_params["selected_table"], 
            test_params["main_com"], 
            test_params["user_info"], 
            test_params["flags"]
        )
        
        print(f"\nTest query_with_subquery:")
        print(f"- date_ranges: {date_ranges}")
        
        # Check that we have a main query date range
        main_date_tuple = date_ranges.get("main", None)
        if main_date_tuple is None:
            # Try to find a suitable alternative if "main" key doesn't exist
            for key in date_ranges:
                if "subquery" not in key.lower():
                    main_date_tuple = date_ranges[key]
                    break
        
        assert main_date_tuple is not None, "Should have a main query date tuple"
        assert isinstance(main_date_tuple, tuple), "Date range should be a tuple"
        assert len(main_date_tuple) == 2, "Date tuple should have exactly 2 elements"
        
        # Validate main query dates
        from_date, to_date = main_date_tuple
        assert check_date_format(from_date), f"From date '{from_date}' is not in YYYYMMDD format"
        assert check_date_format(to_date), f"To date '{to_date}' is not in YYYYMMDD format"
        assert from_date == "20240222", f"Expected from_date '20240222', got '{from_date}'"
        
        # Check subquery date ranges if present
        subquery_keys = [k for k in date_ranges if "subquery" in k.lower()]
        if subquery_keys:
            for subquery_key in subquery_keys:
                subquery_date_tuple = date_ranges[subquery_key]
                print(f"- Subquery {subquery_key} date range: {subquery_date_tuple}")
                
                assert isinstance(subquery_date_tuple, tuple), f"Subquery date range should be a tuple"
                assert len(subquery_date_tuple) == 2, f"Subquery date tuple should have exactly 2 elements"
                
                subq_from, subq_to = subquery_date_tuple
                assert check_date_format(subq_from), f"Subquery from date '{subq_from}' is not in YYYYMMDD format"
                assert check_date_format(subq_to), f"Subquery to date '{subq_to}' is not in YYYYMMDD format"

    def test_query_with_union(self, test_params):
        """Test query containing a UNION operation"""
        query = """
            SELECT bank_nm, acct_no, acct_bal_amt, reg_dt
            FROM aicfo_get_all_amt
            WHERE view_dv = '수시' AND reg_dt = '20240101'
            UNION
            SELECT bank_nm, acct_no, trsc_amt, trsc_dt
            FROM aicfo_get_all_trsc
            WHERE view_dv = '수시' AND trsc_dt = '20240102'
        """
        
        # Run view_table
        transformed_query, date_ranges = view_table(
            query,
            test_params["selected_table"], 
            test_params["main_com"], 
            test_params["user_info"], 
            test_params["flags"]
        )
        
        print(f"\nTest query_with_union:")
        print(f"- date_ranges: {date_ranges}")
        
        # Check that we have date ranges for both parts of the UNION
        assert len(date_ranges) >= 2, "Should have at least 2 date range entries for UNION query"
        
        # Validate each date tuple
        for query_id, date_tuple in date_ranges.items():
            print(f"- Union part {query_id} date range: {date_tuple}")
            
            assert isinstance(date_tuple, tuple), f"Date range for {query_id} should be a tuple"
            assert len(date_tuple) == 2, f"Date tuple for {query_id} should have exactly 2 elements"
            
            from_date, to_date = date_tuple
            assert check_date_format(from_date), f"From date '{from_date}' is not in YYYYMMDD format"
            assert check_date_format(to_date), f"To date '{to_date}' is not in YYYYMMDD format"
            
            # Check expected date values for left and right parts of union
            if "left" in query_id.lower():
                assert from_date == "20240101", f"Left union from_date should be '20240101', got '{from_date}'"
            elif "right" in query_id.lower():
                assert from_date == "20240102", f"Right union from_date should be '20240102', got '{from_date}'"

    def test_query_with_between_date(self, test_params):
        """Test query with BETWEEN date condition"""
        query = """
            SELECT bank_nm, acct_no, acct_bal_amt
            FROM aicfo_get_all_amt
            WHERE view_dv = '수시' 
            AND reg_dt BETWEEN '20240101' AND '20240131'
            AND acct_bal_amt > 1000000
        """
        
        # Run view_table
        transformed_query, date_ranges = view_table(
            query,
            test_params["selected_table"], 
            test_params["main_com"], 
            test_params["user_info"], 
            test_params["flags"]
        )
        
        print(f"\nTest query_with_between_date:")
        print(f"- date_ranges: {date_ranges}")
        
        # Get main date tuple
        main_date_tuple = date_ranges.get("main", list(date_ranges.values())[0])
        
        # Validate tuple format
        assert isinstance(main_date_tuple, tuple), "Date range should be a tuple"
        assert len(main_date_tuple) == 2, "Date tuple should have exactly 2 elements"
        
        from_date, to_date = main_date_tuple
        assert check_date_format(from_date), f"From date '{from_date}' is not in YYYYMMDD format"
        assert check_date_format(to_date), f"To date '{to_date}' is not in YYYYMMDD format"
        
        # Check if BETWEEN dates are correctly extracted
        assert from_date >= "20240101", f"From date '{from_date}' should be >= '20240101'"
        assert to_date <= "20240131", f"To date '{to_date}' should be <= '20240131'"

    def test_query_without_date_condition(self, test_params):
        """Test query without explicit date condition"""
        query = """
            SELECT bank_nm, acct_no, acct_bal_amt
            FROM aicfo_get_all_amt
            WHERE view_dv = '수시' AND acct_bal_amt > 0
        """
        
        # Run view_table
        transformed_query, date_ranges = view_table(
            query,
            test_params["selected_table"], 
            test_params["main_com"], 
            test_params["user_info"], 
            test_params["flags"]
        )
        
        print(f"\nTest query_without_date_condition:")
        print(f"- date_ranges: {date_ranges}")
        
        # Get main date tuple
        main_date_tuple = date_ranges.get("main", list(date_ranges.values())[0])
        
        # Validate tuple format
        assert isinstance(main_date_tuple, tuple), "Date range should be a tuple"
        assert len(main_date_tuple) == 2, "Date tuple should have exactly 2 elements"
        
        from_date, to_date = main_date_tuple
        assert check_date_format(from_date), f"From date '{from_date}' is not in YYYYMMDD format"
        assert check_date_format(to_date), f"To date '{to_date}' is not in YYYYMMDD format"
        
        # Check default date handling (should use today's date)
        today = datetime.now().strftime("%Y%m%d")
        assert from_date == today, f"From date '{from_date}' should default to today '{today}'"
        assert to_date == today, f"To date '{to_date}' should default to today '{today}'"