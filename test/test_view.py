import pytest
from datetime import datetime
from utils.query.view.view_table import view_table

class TestViewTableComplexSubqueries:
    
    def setup_method(self):
        # Test data setup
        self.selected_table = 'amt'
        self.company_id = '테스트회사'
        self.user_info = ('test_user', 'test_intt_id')  # user_id, use_intt_id
        self.flags = {
            'is_joy': False,
            'no_data': False,
            'note_changed': False,
            'future_date': False,
            'invalid_date': False,
            'query_error': False,
            'query_changed': False
        }
        
        # Mock current date for consistent testing
        self.today = datetime.now()
        self.today_str = self.today.strftime("%Y%m%d")
        
    def test_complex_query_with_in_subquery(self):
        """Test that view_table correctly transforms a complex query with IN (subquery)."""
        
        # Complex query with subquery in IN clause
        query = """
        SELECT DISTINCT acct_no, bank_nm 
        FROM aicfo_get_all_amt 
        WHERE view_dv = '수시' AND curr_cd = 'KRW' AND reg_dt = '20250306' 
        AND acct_no IN (
            SELECT DISTINCT acct_no 
            FROM aicfo_get_all_trsc 
            WHERE view_dv = '수시' AND curr_cd = 'KRW' AND trsc_amt >= POWER(10,8) 
            AND trsc_dt BETWEEN '20250106' AND '20250306'
        )
        """
        
        # Call the function being tested
        transformed_query, date_ranges = view_table(
            query_ordered=query,
            selected_table=self.selected_table,
            company_id=self.company_id,
            user_info=self.user_info,
            flags=self.flags
        )
        
        # Print transformed query for inspection
        print(f"\nTransformed Query:\n{transformed_query}")
        print(f"\nDate Ranges:\n{date_ranges}")
        
        # Assertions
        assert transformed_query is not None
        assert len(date_ranges) > 0
        
        # Check if date ranges were correctly extracted
        assert 'main' in date_ranges
        
        # Verify the date range for the main query
        from_date, to_date = date_ranges['main']
        assert from_date == '20250106'  # Should be the earliest date from all parts
        assert to_date == '20250306'  # Should be the latest date from all parts
        
        # Check if the future date flag is set (assuming 2025 is in the future)
        assert self.flags['future_date'] == True
        
        # Verify the transformed query contains view functions
        assert "AICFO_GET_ALL_AMT('" in transformed_query
        assert "AICFO_GET_ALL_TRSC('" in transformed_query
        
        # Verify both view functions have correct parameters
        # Main query view function
        assert f"AICFO_GET_ALL_AMT('{self.user_info[1]}', '{self.user_info[0]}', '{self.company_id}'" in transformed_query
        
        # Subquery view function
        assert f"AICFO_GET_ALL_TRSC('{self.user_info[1]}', '{self.user_info[0]}', '{self.company_id}'" in transformed_query
        
        # Verify dates are included in the query
        # The actual dates might be modified if they're in the future
        assert "20250106" in transformed_query or self.today_str in transformed_query
        assert "20250306" in transformed_query or self.today_str in transformed_query
        
    def test_acct_subquery_with_future_date(self):
        """Test view_table with a complex account subquery with future dates."""
        
        # Complex query with account subquery
        query = """
        SELECT DISTINCT acct_no, bank_nm 
        FROM aicfo_get_all_amt 
        WHERE view_dv = '수시' AND curr_cd = 'KRW' AND reg_dt = '20250306' 
        AND acct_no IN (
            SELECT DISTINCT acct_no 
            FROM aicfo_get_all_trsc 
            WHERE view_dv = '수시' AND curr_cd = 'KRW' AND trsc_amt >= 100000000 
            AND trsc_dt BETWEEN '20250106' AND '20250306'
        )
        """
        
        # Call the function being tested
        transformed_query, date_ranges = view_table(
            query_ordered=query,
            selected_table=self.selected_table,
            company_id=self.company_id,
            user_info=self.user_info,
            flags=self.flags
        )
        
        # Verify future date handling
        assert self.flags['future_date'] == True
        
        # Check if transformed query has today's date for future dates
        today_str = self.today.strftime("%Y%m%d")
        
        # If future date flag is set, the query should use today's date instead
        if '20250306' > today_str:  # This is true as long as we're before 2025
            # Either both dates are replaced with today's date
            # or the earliest non-future date is used as from_date
            main_from_date, main_to_date = date_ranges['main']
            assert main_to_date <= today_str
            
            # Check that there are subquery date ranges as well
            assert len(date_ranges) >= 2
            
    def test_multiple_nested_subqueries(self):
        """Test view_table with multiple nested subqueries."""
        
        # Query with multiple levels of nesting
        query = """
        SELECT bank_nm, acct_no, acct_bal_amt
        FROM aicfo_get_all_amt
        WHERE view_dv = '수시' AND curr_cd = 'KRW' AND reg_dt = '20250306'
        AND acct_no IN (
            SELECT DISTINCT acct_no
            FROM aicfo_get_all_trsc
            WHERE view_dv = '수시' AND curr_cd = 'KRW'
            AND trsc_dt BETWEEN '20250106' AND '20250306'
            AND trsc_amt > (
                SELECT AVG(trsc_amt)
                FROM aicfo_get_all_trsc
                WHERE view_dv = '수시' AND curr_cd = 'KRW'
                AND trsc_dt BETWEEN '20250101' AND '20250306'
            )
        )
        """
        
        # Call the function being tested
        transformed_query, date_ranges = view_table(
            query_ordered=query,
            selected_table=self.selected_table,
            company_id=self.company_id,
            user_info=self.user_info,
            flags=self.flags
        )
        
        # Print for inspection
        print(f"\nMultiple Nested Subqueries Query:\n{transformed_query}")
        print(f"\nDate Ranges:\n{date_ranges}")
        
        # Verify essential transformation aspects
        assert transformed_query is not None
        assert 'main' in date_ranges
        
        # The earliest date should be from the deepest subquery
        from_date, to_date = date_ranges['main']
        assert from_date == '20250101'  # From the deepest subquery
        
        # Verify all view functions are present
        view_function_count = transformed_query.count("AICFO_GET_ALL_")
        assert view_function_count >= 3  # At least 3 view functions should be present