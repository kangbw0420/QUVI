import pytest
from datetime import datetime
from utils.query.view.view_table import ViewTableTransformer

class TestQueryViewFunctionality:
    @pytest.fixture
    def test_env(self):
        """Test environment setup with common parameters"""
        selected_table = "amt"
        user_info = ("test_user", "test_intt")
        view_com = "test_company"
        flags = {"future_date": False}
        
        transformer = ViewTableTransformer(
            selected_table=selected_table,
            user_info=user_info,
            view_com=view_com,
            flags=flags
        )
        
        return transformer

    def test_subquery_with_dates(self, test_env):
        """Test query containing subquery with date conditions"""
        query = """
            SELECT bank_nm, acct_dv, acct_no, acct_bal_amt
            FROM aicfo_get_all_amt
            WHERE reg_dt = '20240222'
            AND acct_no NOT IN (
                SELECT DISTINCT acct_no
                FROM aicfo_get_all_trsc
                WHERE trsc_dt BETWEEN '20241101' AND '20241130'
            )
        """
        
        transformed_query, date_ranges = test_env.transform_query(query)
        
        assert date_ranges["main"] == ("20240222", "20240222")
        assert date_ranges["subquery_1"] == ("20241101", "20241130")
        assert all(date in transformed_query for date in ['20240222', '20241101', '20241130'])

    # def test_greater_than_date(self, test_env):
    #     """Test query with greater than date condition"""
    #     query = """
    #         SELECT bank_nm, acct_no, trsc_amt
    #         FROM aicfo_get_all_trsc
    #         WHERE trsc_dt > '20240201'
    #     """
        
    #     transformed_query, date_ranges = test_env.transform_query(query)
        
    #     assert date_ranges["main"][0] == "20240202"  # Next day after >
    #     assert "'20240202'" in transformed_query

    # def test_less_than_date(self, test_env):
    #     """Test query with less than date condition"""
    #     query = """
    #         SELECT bank_nm, acct_no, trsc_amt
    #         FROM aicfo_get_all_trsc
    #         WHERE trsc_dt < '20240201'
    #     """
        
    #     transformed_query, date_ranges = test_env.transform_query(query)
        
    #     assert date_ranges["main"][1] == "20240131"  # Previous day for <
    #     assert "'20240131'" in transformed_query

    # def test_future_date_handling(self, test_env):
    #     """Test handling of future dates"""
    #     today = datetime.now().strftime("%Y%m%d")
    #     future_date = "20241231"
        
    #     query = f"""
    #         SELECT bank_nm, acct_no, trsc_amt
    #         FROM aicfo_get_all_trsc
    #         WHERE trsc_dt = '{future_date}'
    #     """
        
    #     transformed_query, date_ranges = test_env.transform_query(query)
        
    #     assert test_env.flags["future_date"] is True
    #     assert date_ranges["main"] == (today, today)
    #     assert today in transformed_query

    # def test_multiple_date_columns(self, test_env):
    #     """Test query with multiple date column conditions"""
    #     query = """
    #         SELECT bank_nm, acct_no
    #         FROM aicfo_get_all_amt
    #         WHERE reg_dt = '20240222'
    #         AND due_dt = '20240228'
    #     """
        
    #     transformed_query, date_ranges = test_env.transform_query(query)
        
    #     assert date_ranges["main"] == ("20240222", "20240222")
    #     assert "'20240222'" in transformed_query

    # def test_join_with_dates(self, test_env):
    #     """Test JOIN query with date conditions"""
    #     query = """
    #         SELECT a.bank_nm, a.acct_no, t.trsc_amt
    #         FROM aicfo_get_all_amt a
    #         JOIN aicfo_get_all_trsc t ON a.acct_no = t.acct_no
    #         WHERE a.reg_dt = '20240222'
    #         AND t.trsc_dt = '20240222'
    #     """
        
    #     transformed_query, date_ranges = test_env.transform_query(query)
        
    #     assert date_ranges["main"] == ("20240222", "20240222")
    #     assert "'20240222'" in transformed_query

    # def test_invalid_date_format(self, test_env):
    #     """Test handling of invalid date formats"""
    #     query = """
    #         SELECT bank_nm, acct_no
    #         FROM aicfo_get_all_amt
    #         WHERE reg_dt = 'invalid_date'
    #     """
        
    #     transformed_query, date_ranges = test_env.transform_query(query)
        
    #     today = datetime.now().strftime("%Y%m%d")
    #     assert date_ranges["main"] == (today, today)
    #     assert today in transformed_query

    # def test_complex_date_conditions(self, test_env):
    #     """Test query with complex date conditions"""
    #     query = """
    #         SELECT bank_nm, acct_no
    #         FROM aicfo_get_all_amt
    #         WHERE reg_dt >= '20240201'
    #         AND reg_dt <= '20240229'
    #         AND acct_no IN (
    #             SELECT acct_no
    #             FROM aicfo_get_all_trsc
    #             WHERE trsc_dt BETWEEN '20240215' AND '20240220'
    #         )
    #     """
        
    #     transformed_query, date_ranges = test_env.transform_query(query)
        
    #     assert date_ranges["main"] == ("20240201", "20240229")
    #     assert date_ranges["subquery_1"] == ("20240215", "20240220")
    #     assert all(date in transformed_query for date in 
    #               ['20240201', '20240229', '20240215', '20240220'])
        


    # def test_simple_equal_date(self, test_env):
    #     """Test simple query with equals date condition"""
    #     query = """
    #         SELECT bank_nm, acct_dv, acct_no, acct_bal_amt
    #         FROM aicfo_get_all_amt 
    #         WHERE reg_dt = '20240222'
    #     """
        
    #     transformed_query, date_ranges = test_env.transform_query(query)
        
    #     assert date_ranges["main"] == ("20240222", "20240222")
    #     assert "AICFO_GET_ALL_AMT(" in transformed_query
    #     assert "'20240222'" in transformed_query

    # def test_between_dates(self, test_env):
    #     """Test query with BETWEEN date condition"""
    #     query = """
    #         SELECT bank_nm, acct_no, trsc_amt 
    #         FROM aicfo_get_all_trsc
    #         WHERE trsc_dt BETWEEN '20240101' AND '20240131'
    #     """
        
    #     transformed_query, date_ranges = test_env.transform_query(query)
        
    #     assert date_ranges["main"] == ("20240101", "20240131")
    #     assert "'20240101'" in transformed_query
    #     assert "'20240131'" in transformed_query
    
    # def test_union_query_dates(self, test_env):
    #     """Test UNION query with different date conditions"""
    #     query = """
    #         SELECT bank_nm, acct_no, acct_bal_amt
    #         FROM aicfo_get_all_amt
    #         WHERE reg_dt = '20240222'
    #         UNION
    #         SELECT bank_nm, acct_no, trsc_amt
    #         FROM aicfo_get_all_trsc
    #         WHERE trsc_dt = '20240221'
    #     """
        
    #     transformed_query, date_ranges = test_env.transform_query(query)
        
    #     assert date_ranges["left_union"] == ("20240222", "20240222")
    #     assert date_ranges["right_union"] == ("20240221", "20240221")
    #     assert all(date in transformed_query for date in ['20240222', '20240221'])