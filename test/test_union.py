import pytest
from datetime import datetime
from utils.query.view.view_table import view_table

class TestViewTableComplexQuery:
    
    def setup_method(self):
        # Test data setup
        self.selected_table = 'trsc'
        self.company_id = '뉴젠피앤피'
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
        
    def test_complex_query_with_union_and_subqueries(self):
        """Test processing a complex query with UNION and multiple subqueries."""
        
        # The complex query with subqueries and UNION
        query_ordered = """
        SELECT acct_no FROM (
            SELECT acct_no, COUNT(*) AS transaction_count 
            FROM aicfo_get_all_trsc 
            WHERE view_dv = '수시' AND curr_cd = 'KRW' 
            AND trsc_dt BETWEEN '20250205' AND '20250305' 
            GROUP BY acct_no 
            ORDER BY transaction_count DESC 
            LIMIT 1
        ) 
        UNION 
        SELECT acct_no FROM (
            SELECT acct_no, COUNT(*) AS transaction_count 
            FROM aicfo_get_all_trsc 
            WHERE view_dv = '수시' AND curr_cd = 'KRW' 
            AND trsc_dt BETWEEN '20250105' AND '20250205' 
            GROUP BY acct_no 
            ORDER BY transaction_count ASC 
            LIMIT 1
        )
        """
        
        # Call the function being tested
        transformed_query, date_ranges = view_table(
            query_ordered=query_ordered,
            selected_table=self.selected_table,
            company_id=self.company_id,
            user_info=self.user_info,
            flags=self.flags
        )
        
        # Assertions
        assert transformed_query is not None
        assert len(date_ranges) > 0
        
        # Check if date ranges were correctly extracted
        assert 'main' in date_ranges
        
        # Verify the date range for the main query
        from_date, to_date = date_ranges['main']
        print(transformed_query)
        assert from_date == '20250105'  # Should be the earliest date from all subqueries
        
        # Check if today's date is used if the query has future dates
        if self.flags['future_date']:
            assert to_date <= self.today_str
        else:
            assert to_date == '20250305'  # Should be the latest date from all subqueries
        
        # Check if the transformed query contains the view functions with correct parameters
        assert 'AICFO_GET_ALL_TRSC(' in transformed_query
        
        # Verify company_id is properly included in the query
        assert self.company_id in transformed_query
        
        # Print the transformed query for debugging
        print(f"\nTransformed Query:\n{transformed_query}")
        print(f"\nDate Ranges:\n{date_ranges}")
        
    def test_multiple_subqueries_date_extraction(self):
        """Test that the earliest and latest dates are correctly extracted from multiple subqueries."""
        
        # Query with multiple date ranges in different parts
        query_with_multiple_dates = """
        SELECT acct_no, bank_nm 
        FROM aicfo_get_all_amt 
        WHERE view_dv = '수시' AND reg_dt BETWEEN '20250101' AND '20250131'
        AND acct_no IN (
            SELECT acct_no FROM aicfo_get_all_trsc 
            WHERE trsc_dt BETWEEN '20250201' AND '20250228'
            UNION
            SELECT acct_no FROM aicfo_get_all_trsc 
            WHERE trsc_dt BETWEEN '20250301' AND '20250331'
        )
        """
        
        # Call the function being tested
        transformed_query, date_ranges = view_table(
            query_ordered=query_with_multiple_dates,
            selected_table=self.selected_table,
            company_id=self.company_id,
            user_info=self.user_info,
            flags=self.flags
        )
        
        # Assertions for date ranges
        assert 'main' in date_ranges
        from_date, to_date = date_ranges['main']
        
        # The earliest date should be from the first condition
        assert from_date == '20250101'
        
        # The latest date should be from the last subquery
        assert to_date == '20250331'
        
        # Print results for debugging
        print(f"\nTransformed Query (Multiple Dates):\n{transformed_query}")
        print(f"\nDate Ranges (Multiple Dates):\n{date_ranges}")