import unittest
import sys
import os
from datetime import datetime, timedelta
from typing import Tuple, Dict

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module to test
from utils.query.view_table import (
    add_view_table,
    extract_view_date,
    has_subquery,
    has_union
)

class ViewTableDateTest(unittest.TestCase):
    def setUp(self):
        # Common test parameters
        self.selected_table = "amt"
        self.view_com = "테스트회사"
        self.user_info = ("test_user", "test_intt_id")
        self.view_date = ("20240101", "20240131")
        self.flags = {"future_date": False}
        
        # Today's date for testing
        self.today = datetime.now().strftime("%Y%m%d")
        self.yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        self.last_week = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
        self.next_month = (datetime.now() + timedelta(days=30)).strftime("%Y%m%d")

    def test_basic_functionality(self):
        """Basic test for query transformation"""
        query = "SELECT * FROM aicfo_get_all_amt WHERE reg_dt = '20240101'"
        result = add_view_table(
            query, self.selected_table, self.view_com,
            self.user_info, self.view_date, self.flags
        )
        
        expected_part = f"aicfo_get_all_amt('test_intt_id', 'test_user', '테스트회사', '20240101', '20240131')"
        self.assertIn(expected_part, result)

    def test_subquery_with_different_dates(self):
        """Test main query with one date and subquery with another date"""
        query = f"""
        SELECT a.* FROM aicfo_get_all_amt a
        WHERE a.reg_dt = '{self.yesterday}'
        AND a.acct_no IN (
            SELECT b.acct_no FROM aicfo_get_all_trsc b WHERE b.trsc_dt = '{self.last_week}'
        )
        """
        
        # Extract dates first to update flags if needed
        main_date = extract_view_date(query, "amt", self.flags)
        self.assertEqual(main_date, (self.yesterday, self.yesterday))
        
        # Now transform the query
        result = add_view_table(
            query, self.selected_table, self.view_com,
            self.user_info, main_date, self.flags
        )
        
        # Both tables should be transformed with the same date parameters
        main_table = f"aicfo_get_all_amt('test_intt_id', 'test_user', '테스트회사', '{self.yesterday}', '{self.yesterday}') a"
        sub_table = f"aicfo_get_all_trsc('test_intt_id', 'test_user', '테스트회사', '{self.yesterday}', '{self.yesterday}') b"
        
        self.assertIn(main_table, result)
        self.assertIn(sub_table, result)
        self.assertIn(f"b.trsc_dt = '{self.last_week}'", result)  # Original date condition preserved

    def test_nested_subqueries_with_different_dates(self):
        """Test nested subqueries with different date conditions"""
        query = f"""
        SELECT main.* FROM aicfo_get_all_amt main
        WHERE main.reg_dt BETWEEN '{self.last_week}' AND '{self.yesterday}'
        AND main.acct_no IN (
            SELECT t.acct_no FROM aicfo_get_all_trsc t 
            WHERE t.trsc_dt = '{self.yesterday}'
            AND t.bank_nm IN (
                SELECT s.bank_nm FROM aicfo_get_all_stock s 
                WHERE s.reg_dt = '{self.today}'
            )
        )
        """
        
        # Extract dates first
        main_date = extract_view_date(query, "amt", self.flags)
        self.assertEqual(main_date, (self.last_week, self.yesterday))
        
        # Now transform the query
        result = add_view_table(
            query, self.selected_table, self.view_com,
            self.user_info, main_date, self.flags
        )
        
        # All tables should be transformed with the same date parameters from main query
        main_table = f"aicfo_get_all_amt('test_intt_id', 'test_user', '테스트회사', '{self.last_week}', '{self.yesterday}') main"
        trsc_table = f"aicfo_get_all_trsc('test_intt_id', 'test_user', '테스트회사', '{self.last_week}', '{self.yesterday}') t"
        stock_table = f"aicfo_get_all_stock('test_intt_id', 'test_user', '테스트회사', '{self.last_week}', '{self.yesterday}') s"
        
        self.assertIn(main_table, result)
        self.assertIn(trsc_table, result)
        self.assertIn(stock_table, result)
        
        # Original date conditions should be preserved
        self.assertIn(f"main.reg_dt BETWEEN '{self.last_week}' AND '{self.yesterday}'", result)
        self.assertIn(f"t.trsc_dt = '{self.yesterday}'", result)
        self.assertIn(f"s.reg_dt = '{self.today}'", result)

    def test_future_date_in_subquery(self):
        """Test future date in subquery gets transformed in view function but preserved in WHERE"""
        query = f"""
        SELECT a.* FROM aicfo_get_all_amt a
        WHERE a.reg_dt = '{self.yesterday}'
        AND a.acct_no IN (
            SELECT b.acct_no FROM aicfo_get_all_trsc b WHERE b.trsc_dt = '{self.next_month}'
        )
        """
        
        # Extract dates and check flags
        flags = {"future_date": False}
        main_date = extract_view_date(query, "amt", flags)
        self.assertEqual(main_date, (self.yesterday, self.yesterday))
        self.assertTrue(flags["future_date"])  # Should be set to True due to future date
        
        # Now transform the query
        result = add_view_table(
            query, self.selected_table, self.view_com,
            self.user_info, main_date, flags
        )
        
        # Both tables should be transformed with the same date parameters from main query
        main_table = f"aicfo_get_all_amt('test_intt_id', 'test_user', '테스트회사', '{self.yesterday}', '{self.yesterday}') a"
        sub_table = f"aicfo_get_all_trsc('test_intt_id', 'test_user', '테스트회사', '{self.yesterday}', '{self.yesterday}') b"
        
        self.assertIn(main_table, result)
        self.assertIn(sub_table, result)
        self.assertIn(f"b.trsc_dt = '{self.next_month}'", result)  # Future date preserved in condition

    def test_complex_join_with_different_dates(self):
        """Test complex query with JOIN and subqueries with different dates"""
        query = f"""
        SELECT main.*, j.trsc_amt 
        FROM aicfo_get_all_amt main
        JOIN aicfo_get_all_trsc j ON main.acct_no = j.acct_no AND j.trsc_dt BETWEEN '{self.last_week}' AND '{self.yesterday}'
        WHERE main.reg_dt = '{self.today}'
        AND main.bank_nm IN (
            SELECT s.bank_nm 
            FROM aicfo_get_all_stock s 
            WHERE s.reg_dt = '{self.yesterday}'
        )
        """
        
        # Extract dates
        main_date = extract_view_date(query, "amt", self.flags)
        self.assertEqual(main_date, (self.today, self.today))
        
        # Transform query
        result = add_view_table(
            query, self.selected_table, self.view_com,
            self.user_info, main_date, self.flags
        )
        
        # All tables should use the same date parameters
        main_table = f"aicfo_get_all_amt('test_intt_id', 'test_user', '테스트회사', '{self.today}', '{self.today}') main"
        join_table = f"aicfo_get_all_trsc('test_intt_id', 'test_user', '테스트회사', '{self.today}', '{self.today}') j"
        stock_table = f"aicfo_get_all_stock('test_intt_id', 'test_user', '테스트회사', '{self.today}', '{self.today}') s"
        
        self.assertIn(main_table, result)
        self.assertIn(join_table, result)
        self.assertIn(stock_table, result)
        
        # Original date conditions should be preserved
        self.assertIn(f"main.reg_dt = '{self.today}'", result)
        self.assertIn(f"j.trsc_dt BETWEEN '{self.last_week}' AND '{self.yesterday}'", result)
        self.assertIn(f"s.reg_dt = '{self.yesterday}'", result)

    def test_union_with_different_dates(self):
        """Test UNION queries with different dates"""
        query = f"""
        SELECT a.acct_no, a.acct_bal_amt
        FROM aicfo_get_all_amt a
        WHERE a.reg_dt = '{self.yesterday}'
        UNION
        SELECT b.acct_no, b.acct_bal_amt
        FROM aicfo_get_all_amt b
        WHERE b.reg_dt = '{self.today}'
        """
        
        # Extract dates - should use the first part's date
        main_date = extract_view_date(query, "amt", self.flags)
        self.assertEqual(main_date, (self.yesterday, self.yesterday))
        
        # Transform query
        result = add_view_table(
            query, self.selected_table, self.view_com,
            self.user_info, main_date, self.flags
        )
        
        # Both parts should be transformed
        first_part = f"aicfo_get_all_amt('test_intt_id', 'test_user', '테스트회사', '{self.yesterday}', '{self.yesterday}') a"
        second_part = f"aicfo_get_all_amt('test_intt_id', 'test_user', '테스트회사', '{self.yesterday}', '{self.yesterday}') b"
        
        self.assertIn(first_part, result)
        self.assertIn(second_part, result)
        self.assertIn(f"a.reg_dt = '{self.yesterday}'", result)
        self.assertIn(f"b.reg_dt = '{self.today}'", result)

    def test_union_with_subqueries(self):
        """Test UNION with subqueries containing different dates"""
        query = f"""
        SELECT a.acct_no, a.acct_bal_amt
        FROM aicfo_get_all_amt a
        WHERE a.reg_dt = '{self.yesterday}'
        AND a.acct_no IN (
            SELECT t1.acct_no FROM aicfo_get_all_trsc t1 WHERE t1.trsc_dt = '{self.last_week}'
        )
        UNION
        SELECT b.acct_no, b.acct_bal_amt
        FROM aicfo_get_all_amt b
        WHERE b.reg_dt = '{self.today}'
        AND b.acct_no IN (
            SELECT t2.acct_no FROM aicfo_get_all_trsc t2 WHERE t2.trsc_dt = '{self.yesterday}'
        )
        """
        
        # Extract dates - should use the first part's date
        main_date = extract_view_date(query, "amt", self.flags)
        self.assertEqual(main_date, (self.yesterday, self.yesterday))
        
        # Transform query
        result = add_view_table(
            query, self.selected_table, self.view_com,
            self.user_info, main_date, self.flags
        )
        
        # All tables should be transformed
        self.assertIn(f"aicfo_get_all_amt('test_intt_id', 'test_user', '테스트회사', '{self.yesterday}', '{self.yesterday}') a", result)
        self.assertIn(f"aicfo_get_all_trsc('test_intt_id', 'test_user', '테스트회사', '{self.yesterday}', '{self.yesterday}') t1", result)
        self.assertIn(f"aicfo_get_all_amt('test_intt_id', 'test_user', '테스트회사', '{self.yesterday}', '{self.yesterday}') b", result)
        self.assertIn(f"aicfo_get_all_trsc('test_intt_id', 'test_user', '테스트회사', '{self.yesterday}', '{self.yesterday}') t2", result)
        
        # Original date conditions should be preserved
        self.assertIn(f"a.reg_dt = '{self.yesterday}'", result)
        self.assertIn(f"t1.trsc_dt = '{self.last_week}'", result)
        self.assertIn(f"b.reg_dt = '{self.today}'", result)
        self.assertIn(f"t2.trsc_dt = '{self.yesterday}'", result)

    def test_between_with_future_end_date(self):
        """Test BETWEEN clause with future end date should modify view function dates"""
        query = f"""
        SELECT * FROM aicfo_get_all_amt
        WHERE reg_dt BETWEEN '{self.yesterday}' AND '{self.next_month}'
        """
        
        # Extract dates - should set future_date flag
        flags = {"future_date": False}
        main_date = extract_view_date(query, "amt", flags)
        self.assertEqual(main_date[0], self.yesterday)
        self.assertEqual(main_date[1], self.today)  # Should be changed to today
        self.assertTrue(flags["future_date"])
        
        # Transform query
        result = add_view_table(
            query, self.selected_table, self.view_com,
            self.user_info, main_date, flags
        )
        
        # Table should be transformed with corrected date range
        self.assertIn(f"aicfo_get_all_amt('test_intt_id', 'test_user', '테스트회사', '{self.yesterday}', '{self.today}')", result)
        # But original condition preserved
        self.assertIn(f"reg_dt BETWEEN '{self.yesterday}' AND '{self.next_month}'", result)

    def test_different_date_ranges_in_subquery(self):
        """Test subquery with completely different date range"""
        query = """
        SELECT DISTINCT acct_no, bank_nm 
        FROM aicfo_get_all_amt 
        WHERE view_dv = '수시' AND curr_cd = 'KRW' AND reg_dt = '20250220' 
        AND acct_no NOT IN (
            SELECT DISTINCT acct_no 
            FROM aicfo_get_all_trsc 
            WHERE view_dv = '수시' AND curr_cd = 'KRW' AND trsc_dt > '20241120'
        )
        """
        
        # Extract dates from main query
        main_date = extract_view_date(query, "amt", self.flags)
        self.assertEqual(main_date, ('20250220', '20250220'))
        self.assertTrue(self.flags["future_date"])  # Future date detected
        
        # Now we need to separately extract dates from subquery
        subquery = "SELECT DISTINCT acct_no FROM aicfo_get_all_trsc WHERE view_dv = '수시' AND curr_cd = 'KRW' AND trsc_dt > '20241120'"
        sub_flags = {"future_date": False}
        sub_date = extract_view_date(subquery, "trsc", sub_flags)
        self.assertEqual(sub_date, ('20241120', self.today))  # Should be from 20241120 to today

if __name__ == "__main__":
    unittest.main()