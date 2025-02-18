import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from utils.query.view_table import extract_view_date, add_view_table

class TestViewTable(unittest.TestCase):
    def setUp(self):
        self.flags = {
            "no_data": False,
            "future_date": False,
            "past_date": False
        }
        self.today = datetime.now().strftime("%Y%m%d")
        self.yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        self.tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
        self.user_info = ("test_user", "test_intt_id")

    def test_simple_query_extract_view_date(self):
        # 단순 날짜 조건을 가진 쿼리
        query = f"SELECT * FROM aicfo_get_all_amt WHERE com_nm = '테스트' AND reg_dt = '{self.today}'"
        result = extract_view_date(query, "amt", self.flags)
        self.assertEqual(result, (self.today, self.today))
        self.assertFalse(self.flags["future_date"])

    def test_between_date_query_extract_view_date(self):
        # BETWEEN 조건을 가진 쿼리
        query = f"SELECT * FROM aicfo_get_all_trsc WHERE com_nm = '테스트' AND trsc_dt BETWEEN '{self.yesterday}' AND '{self.today}'"
        result = extract_view_date(query, "trsc", self.flags)
        self.assertEqual(result, (self.yesterday, self.today))
        self.assertFalse(self.flags["future_date"])
        
    def test_future_date_query_extract_view_date(self):
        # 미래 날짜 조건을 가진 쿼리 (future_date 플래그 체크)
        query = f"SELECT * FROM aicfo_get_all_trsc WHERE com_nm = '테스트' AND trsc_dt = '{self.tomorrow}'"
        result = extract_view_date(query, "trsc", self.flags)
        self.assertEqual(result, (self.today, self.today))  # 미래 날짜가 오늘로 변경됨
        self.assertTrue(self.flags["future_date"])
        
    def test_inequality_date_query_extract_view_date(self):
        # 부등호 날짜 조건을 가진 쿼리
        query = f"SELECT * FROM aicfo_get_all_trsc WHERE com_nm = '테스트' AND trsc_dt >= '{self.yesterday}' AND trsc_dt <= '{self.today}'"
        result = extract_view_date(query, "trsc", self.flags)
        self.assertEqual(result, (self.yesterday, self.today))
        self.assertFalse(self.flags["future_date"])
        
    def test_subquery_extract_view_date(self):
        # 서브쿼리를 포함한 쿼리
        query = f"""
        SELECT COUNT(*) as count 
        FROM (
            SELECT trsc_dt, SUM(CASE WHEN in_out_dv = '출금' THEN trsc_amt ELSE 0 END) as out_amt 
            FROM aicfo_get_all_trsc 
            WHERE com_nm = '테스트' AND trsc_dt BETWEEN '{self.yesterday}' AND '{self.today}'
            GROUP BY trsc_dt
        ) subquery
        """
        result = extract_view_date(query, "trsc", self.flags)
        self.assertEqual(result, (self.yesterday, self.today))
        self.assertFalse(self.flags["future_date"])
        
    def test_complex_subquery_extract_view_date(self):
        # 복잡한 서브쿼리를 포함한 쿼리
        query = f"""
        SELECT COUNT(*) as out_more_days 
        FROM (
            SELECT trsc_dt, SUM(CASE WHEN in_out_dv = '출금' THEN trsc_amt ELSE 0 END) as out_amt,
                          SUM(CASE WHEN in_out_dv = '입금' THEN trsc_amt ELSE 0 END) as in_amt 
            FROM aicfo_get_all_trsc 
            WHERE com_nm = '테스트' AND view_dv = '수시' AND curr_cd = 'KRW' 
                  AND trsc_dt BETWEEN '{self.yesterday}' AND '{self.today}'
            GROUP BY trsc_dt 
            HAVING SUM(CASE WHEN in_out_dv = '출금' THEN trsc_amt ELSE 0 END) > 
                   SUM(CASE WHEN in_out_dv = '입금' THEN trsc_amt ELSE 0 END)
        ) subquery
        """
        result = extract_view_date(query, "trsc", self.flags)
        self.assertEqual(result, (self.yesterday, self.today))
        self.assertFalse(self.flags["future_date"])
        
    def test_no_date_query_extract_view_date(self):
        # 날짜 조건이 없는 쿼리
        query = "SELECT * FROM aicfo_get_all_amt WHERE com_nm = '테스트'"
        result = extract_view_date(query, "amt", self.flags)
        self.assertEqual(result, (self.today, self.today))  # 기본값으로 오늘 날짜를 사용
        self.assertFalse(self.flags["future_date"])
        
    def test_simple_query_add_view_table(self):
        # 단순 쿼리 변환
        query = "SELECT * FROM aicfo_get_all_amt WHERE com_nm = '테스트'"
        view_date = (self.yesterday, self.today)
        result = add_view_table(query, "amt", "테스트회사", self.user_info, view_date, self.flags)
        expected = f"SELECT * FROM aicfo_get_all_amt('test_intt_id', 'test_user', '테스트회사', '{self.yesterday}', '{self.today}') WHERE com_nm = '테스트'"
        self.assertEqual(result, expected)
        
    def test_complex_query_add_view_table(self):
        # ORDER BY, LIMIT을 포함한 복잡한 쿼리 변환
        query = "SELECT * FROM aicfo_get_all_trsc WHERE com_nm = '테스트' ORDER BY trsc_dt DESC LIMIT 10"
        view_date = (self.yesterday, self.today)
        result = add_view_table(query, "trsc", "테스트회사", self.user_info, view_date, self.flags)
        expected = f"SELECT * FROM aicfo_get_all_trsc('test_intt_id', 'test_user', '테스트회사', '{self.yesterday}', '{self.today}') WHERE com_nm = '테스트' ORDER BY trsc_dt DESC LIMIT 10"
        self.assertEqual(result, expected)
        
    def test_subquery_add_view_table(self):
        # 서브쿼리를 포함한 쿼리 변환
        query = """
        SELECT COUNT(*) as count 
        FROM (
            SELECT trsc_dt FROM aicfo_get_all_trsc 
            WHERE com_nm = '테스트' 
            GROUP BY trsc_dt
        ) subquery
        """
        view_date = (self.yesterday, self.today)
        result = add_view_table(query, "trsc", "테스트회사", self.user_info, view_date, self.flags)
        
        # 서브쿼리를 포함하는 쿼리의 변환 결과 확인
        self.assertIn("aicfo_get_all_trsc('test_intt_id', 'test_user', '테스트회사',", result)
        self.assertIn(f"'{self.yesterday}', '{self.today}'", result)
        
    def test_complex_subquery_add_view_table(self):
        # 복잡한 서브쿼리를 포함한 쿼리 변환
        query = """
        SELECT COUNT(*) as out_more_days 
        FROM (
            SELECT trsc_dt, SUM(CASE WHEN in_out_dv = '출금' THEN trsc_amt ELSE 0 END) as out_amt,
                          SUM(CASE WHEN in_out_dv = '입금' THEN trsc_amt ELSE 0 END) as in_amt 
            FROM aicfo_get_all_trsc 
            WHERE com_nm = '테스트' AND view_dv = '수시' AND curr_cd = 'KRW'
            GROUP BY trsc_dt 
            HAVING SUM(CASE WHEN in_out_dv = '출금' THEN trsc_amt ELSE 0 END) > 
                   SUM(CASE WHEN in_out_dv = '입금' THEN trsc_amt ELSE 0 END)
        ) subquery
        """
        view_date = (self.yesterday, self.today)
        result = add_view_table(query, "trsc", "테스트회사", self.user_info, view_date, self.flags)
        
        # 복잡한 서브쿼리를 포함하는 쿼리의 변환 결과 확인
        self.assertIn("aicfo_get_all_trsc('test_intt_id', 'test_user', '테스트회사',", result)
        self.assertIn(f"'{self.yesterday}', '{self.today}'", result)

if __name__ == '__main__':
    unittest.main()