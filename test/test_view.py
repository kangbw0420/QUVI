import sys
import unittest
from datetime import datetime
import os
from unittest.mock import patch

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.query.view_table import has_subquery, add_view_table, extract_view_date

class TestViewTable(unittest.TestCase):
    def setUp(self):
        self.user_info = ('user123', 'intt456')
        self.view_com = 'TestCompany'
        self.flags = {'future_date': False, 'past_date': False}
        self.today = datetime.now().strftime("%Y%m%d")
        
    def test_has_subquery(self):
        # Test a query with subquery
        query_with_subquery = """
        SELECT DISTINCT acct_no, bank_nm FROM aicfo_get_all_amt 
        WHERE view_dv = '수시' AND curr_cd = 'KRW' AND trsc_dt = '20250219' 
        AND acct_no NOT IN (
            SELECT DISTINCT acct_no FROM aicfo_get_all_trsc 
            WHERE view_dv = '수시' AND curr_cd = 'KRW' AND trsc_dt > '20241119'
        );
        """
        self.assertTrue(has_subquery(query_with_subquery))
        
        # Test a simple query without subquery
        simple_query = "SELECT * FROM aicfo_get_all_amt WHERE view_dv = '수시';"
        self.assertFalse(has_subquery(simple_query))
        
    def test_add_view_table_with_subquery(self):
        query = """
        SELECT DISTINCT acct_no, bank_nm FROM aicfo_get_all_amt 
        WHERE view_dv = '수시' AND curr_cd = 'KRW' AND trsc_dt = '20250219' 
        AND acct_no NOT IN (
            SELECT DISTINCT acct_no FROM aicfo_get_all_trsc 
            WHERE view_dv = '수시' AND curr_cd = 'KRW' AND trsc_dt > '20241119'
        );
        """
        selected_table = 'amt'
        view_date = ('20250219', '20250219')
        
        modified_query = add_view_table(query, selected_table, self.view_com, 
                                        self.user_info, view_date, self.flags)
        
        print("\nOriginal query:")
        print(query)
        print("\nModified query:")
        print(modified_query)
        
        # Check that both table references were properly transformed
        self.assertIn("aicfo_get_all_amt('intt456', 'user123', 'TestCompany', '20250219', '20250219')", modified_query)
        self.assertIn("aicfo_get_all_trsc('intt456', 'user123', 'TestCompany', '20250219', '20250219')", modified_query)
        
        # Ensure the structure is preserved
        self.assertIn("acct_no NOT IN", modified_query)
        self.assertIn("view_dv = '수시'", modified_query)
        
    def test_extract_view_date_with_subquery(self):
        query = """
        SELECT DISTINCT acct_no, bank_nm FROM aicfo_get_all_amt 
        WHERE view_dv = '수시' AND curr_cd = 'KRW' AND reg_dt = '20250219' 
        AND acct_no NOT IN (
            SELECT DISTINCT acct_no FROM aicfo_get_all_trsc 
            WHERE view_dv = '수시' AND curr_cd = 'KRW' AND trsc_dt > '20241119'
        );
        """
        selected_table = 'amt'
        
        view_date = extract_view_date(query, selected_table, self.flags)
        
        print(f"\nExtracted view date: {view_date}")
        self.assertEqual(view_date, ('20250219', '20250219'))
        
    def test_add_view_table_with_complex_subquery(self):
        query = """
        SELECT a.acct_no, a.bank_nm, a.acct_bal_amt
        FROM aicfo_get_all_amt a
        WHERE a.view_dv = '수시' 
        AND a.acct_no IN (
            SELECT t.acct_no 
            FROM aicfo_get_all_trsc t
            WHERE t.trsc_dt BETWEEN '20250101' AND '20250131'
            AND t.in_out_dv = '입금'
        )
        ORDER BY a.acct_bal_amt DESC;
        """
        selected_table = 'amt'
        view_date = ('20250101', '20250131')
        
        modified_query = add_view_table(query, selected_table, self.view_com, 
                                        self.user_info, view_date, self.flags)
        
        print("\nOriginal complex query:")
        print(query)
        print("\nModified complex query:")
        print(modified_query)
        
        # Check that both table references were properly transformed with aliases
        self.assertIn("aicfo_get_all_amt('intt456', 'user123', 'TestCompany', '20250101', '20250131') a", modified_query)
        self.assertIn("aicfo_get_all_trsc('intt456', 'user123', 'TestCompany', '20250101', '20250131') t", modified_query)
        
        # Ensure the structure is preserved
        self.assertIn("a.acct_no IN", modified_query)
        self.assertIn("t.in_out_dv = '입금'", modified_query)

if __name__ == '__main__':
    unittest.main()