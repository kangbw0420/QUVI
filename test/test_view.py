import unittest
from datetime import datetime
from typing import Tuple

# view_table.py에서 테스트할 함수 임포트
from utils.query.view_table import add_view_table, extract_view_date

class ViewTableTest(unittest.TestCase):
    def setUp(self):
        # 테스트에 필요한 공통 변수 설정
        self.selected_table = "amt"
        self.view_com = "테스트회사"
        self.user_info = ("test_user", "test_intt")
        self.view_date = ("20240101", "20240131")
        self.flags = {"future_date": False}
        
    def test_simple_query(self):
        """기본적인 단일 테이블 쿼리 테스트"""
        query = "SELECT * FROM aicfo_get_all_amt WHERE view_dv = '수시' AND reg_dt = '20240115'"
        expected = "SELECT * FROM aicfo_get_all_amt('test_intt', 'test_user', '테스트회사', '20240101', '20240131') WHERE view_dv = '수시' AND reg_dt = '20240115'"
        
        result = add_view_table(query, self.selected_table, self.view_com, self.user_info, self.view_date, self.flags)
        self.assertEqual(result, expected)
        
    def test_query_with_alias(self):
        """테이블 별칭을 포함한 쿼리 테스트"""
        query = "SELECT a.acct_no, a.acct_bal_amt FROM aicfo_get_all_amt a WHERE a.view_dv = '예적금' AND a.reg_dt = '20240115'"
        expected = "SELECT a.acct_no, a.acct_bal_amt FROM aicfo_get_all_amt('test_intt', 'test_user', '테스트회사', '20240101', '20240131') a WHERE a.view_dv = '예적금' AND a.reg_dt = '20240115'"
        
        result = add_view_table(query, self.selected_table, self.view_com, self.user_info, self.view_date, self.flags)
        self.assertEqual(result, expected)
        
    def test_query_with_subquery(self):
        """서브쿼리를 포함한 쿼리 테스트"""
        query = """
        SELECT main.acct_no, main.acct_bal_amt 
        FROM aicfo_get_all_amt main
        WHERE main.acct_no IN (
            SELECT sub.acct_no 
            FROM aicfo_get_all_amt sub 
            WHERE sub.reg_dt = '20240101'
        ) AND main.reg_dt = '20240131'
        """
        expected = """
        SELECT main.acct_no, main.acct_bal_amt 
        FROM aicfo_get_all_amt('test_intt', 'test_user', '테스트회사', '20240101', '20240131') main
        WHERE main.acct_no IN (
            SELECT sub.acct_no 
            FROM aicfo_get_all_amt('test_intt', 'test_user', '테스트회사', '20240101', '20240131') sub 
            WHERE sub.reg_dt = '20240101'
        ) AND main.reg_dt = '20240131'
        """
        
        result = add_view_table(query, self.selected_table, self.view_com, self.user_info, self.view_date, self.flags)
        # 공백 정규화하여 비교
        self.assertEqual(' '.join(result.split()), ' '.join(expected.split()))
        
    def test_query_with_join(self):
        """JOIN을 포함한 쿼리 테스트"""
        query = """
        SELECT a.acct_no, a.acct_bal_amt, b.trsc_amt
        FROM aicfo_get_all_amt a
        JOIN aicfo_get_all_trsc b ON a.acct_no = b.acct_no
        WHERE a.reg_dt = '20240115' AND b.trsc_dt = '20240115'
        """
        expected = """
        SELECT a.acct_no, a.acct_bal_amt, b.trsc_amt
        FROM aicfo_get_all_amt('test_intt', 'test_user', '테스트회사', '20240101', '20240131') a
        JOIN aicfo_get_all_trsc('test_intt', 'test_user', '테스트회사', '20240101', '20240131') b ON a.acct_no = b.acct_no
        WHERE a.reg_dt = '20240115' AND b.trsc_dt = '20240115'
        """
        
        result = add_view_table(query, self.selected_table, self.view_com, self.user_info, self.view_date, self.flags)
        # 공백 정규화하여 비교
        self.assertEqual(' '.join(result.split()), ' '.join(expected.split()))
        
    def test_query_with_join_as_keyword(self):
        """AS 키워드가 있는 JOIN을 포함한 쿼리 테스트"""
        query = """
        SELECT a.acct_no, a.acct_bal_amt, b.trsc_amt
        FROM aicfo_get_all_amt AS a
        JOIN aicfo_get_all_trsc AS b ON a.acct_no = b.acct_no
        WHERE a.reg_dt = '20240115' AND b.trsc_dt = '20240115'
        """
        expected = """
        SELECT a.acct_no, a.acct_bal_amt, b.trsc_amt
        FROM aicfo_get_all_amt('test_intt', 'test_user', '테스트회사', '20240101', '20240131') AS a
        JOIN aicfo_get_all_trsc('test_intt', 'test_user', '테스트회사', '20240101', '20240131') AS b ON a.acct_no = b.acct_no
        WHERE a.reg_dt = '20240115' AND b.trsc_dt = '20240115'
        """
        
        result = add_view_table(query, self.selected_table, self.view_com, self.user_info, self.view_date, self.flags)
        # 공백 정규화하여 비교
        self.assertEqual(' '.join(result.split()), ' '.join(expected.split()))
        
    def test_query_with_multiple_joins(self):
        """여러 JOIN을 포함한 쿼리 테스트"""
        query = """
        SELECT a.acct_no, a.acct_bal_amt, b.trsc_amt, c.bal_qunt
        FROM aicfo_get_all_amt a
        JOIN aicfo_get_all_trsc b ON a.acct_no = b.acct_no
        JOIN aicfo_get_all_stock c ON a.acct_no = c.acct_no
        WHERE a.reg_dt = '20240115'
        """
        expected = """
        SELECT a.acct_no, a.acct_bal_amt, b.trsc_amt, c.bal_qunt
        FROM aicfo_get_all_amt('test_intt', 'test_user', '테스트회사', '20240101', '20240131') a
        JOIN aicfo_get_all_trsc('test_intt', 'test_user', '테스트회사', '20240101', '20240131') b ON a.acct_no = b.acct_no
        JOIN aicfo_get_all_stock('test_intt', 'test_user', '테스트회사', '20240101', '20240131') c ON a.acct_no = c.acct_no
        WHERE a.reg_dt = '20240115'
        """
        
        result = add_view_table(query, self.selected_table, self.view_com, self.user_info, self.view_date, self.flags)
        # 공백 정규화하여 비교
        self.assertEqual(' '.join(result.split()), ' '.join(expected.split()))
    
    def test_query_with_join_and_subquery(self):
        """JOIN과 서브쿼리를 모두 포함한 복잡한 쿼리 테스트"""
        query = """
        SELECT a.acct_no, a.acct_bal_amt, b.trsc_amt,
            (SELECT AVG(sub.acct_bal_amt) FROM aicfo_get_all_amt sub WHERE sub.reg_dt BETWEEN '20240101' AND '20240131') as avg_bal
        FROM aicfo_get_all_amt a
        JOIN aicfo_get_all_trsc b ON a.acct_no = b.acct_no
        WHERE a.reg_dt = '20240115' AND a.acct_no IN (
            SELECT DISTINCT c.acct_no FROM aicfo_get_all_trsc c WHERE c.trsc_dt >= '20240101'
        )
        """
        expected = """
        SELECT a.acct_no, a.acct_bal_amt, b.trsc_amt,
            (SELECT AVG(sub.acct_bal_amt) FROM aicfo_get_all_amt('test_intt', 'test_user', '테스트회사', '20240101', '20240131') sub WHERE sub.reg_dt BETWEEN '20240101' AND '20240131') as avg_bal
        FROM aicfo_get_all_amt('test_intt', 'test_user', '테스트회사', '20240101', '20240131') a
        JOIN aicfo_get_all_trsc('test_intt', 'test_user', '테스트회사', '20240101', '20240131') b ON a.acct_no = b.acct_no
        WHERE a.reg_dt = '20240115' AND a.acct_no IN (
            SELECT DISTINCT c.acct_no FROM aicfo_get_all_trsc('test_intt', 'test_user', '테스트회사', '20240101', '20240131') c WHERE c.trsc_dt >= '20240101'
        )
        """
        
        result = add_view_table(query, self.selected_table, self.view_com, self.user_info, self.view_date, self.flags)
        # 공백 정규화하여 비교
        self.assertEqual(' '.join(result.split()), ' '.join(expected.split()))
    
    def test_extract_view_date_simple(self):
        """기본 날짜 추출 테스트"""
        query = "SELECT * FROM table WHERE reg_dt = '20240115'"
        flags = {}
        result = extract_view_date(query, "amt", flags)
        self.assertEqual(result, ("20240115", "20240115"))
        
    def test_extract_view_date_between(self):
        """BETWEEN 조건 날짜 추출 테스트"""
        query = "SELECT * FROM table WHERE reg_dt BETWEEN '20240101' AND '20240131'"
        flags = {}
        result = extract_view_date(query, "amt", flags)
        self.assertEqual(result, ("20240101", "20240131"))
        
    def test_extract_view_date_inequality(self):
        """부등호 조건 날짜 추출 테스트"""
        query = "SELECT * FROM table WHERE reg_dt >= '20240101' AND reg_dt <= '20240131'"
        flags = {}
        result = extract_view_date(query, "amt", flags)
        self.assertEqual(result, ("20240101", "20240131"))
        
    def test_extract_view_date_future(self):
        """미래 날짜 처리 테스트"""
        # 현재 날짜보다 1년 뒤 날짜 생성
        today = datetime.now()
        future_year = today.year + 1
        future_date = f"{future_year}0101"
        
        query = f"SELECT * FROM table WHERE reg_dt = '{future_date}'"
        flags = {}
        result = extract_view_date(query, "amt", flags)
        
        # 미래 날짜가 오늘로 조정되었는지 확인
        self.assertTrue(flags.get("future_date", False))
        today_str = datetime.now().strftime("%Y%m%d")
        self.assertEqual(result, (today_str, today_str))

    def test_complex_query_with_different_dates(self):
        """서로 다른 날짜를 가진 복잡한 쿼리 테스트"""
        query = """
        SELECT jan1.acct_no
         , ( (jan1.total_appr_amt - jan1.deposit_amt) / NULLIF (jan1.deposit_amt, 0) ) * 100 AS return_rate_jan1
         , ( (today.total_appr_amt - today.deposit_amt) / NULLIF (today.deposit_amt, 0) ) * 100 AS return_rate_today
         FROM aicfo_get_all_amt jan1
         JOIN aicfo_get_all_amt today
         ON jan1.acct_no = today.acct_no
         WHERE com_nm = '비즈플레이'
         AND jan1.view_dv = '증권'
         AND jan1.curr_cd = 'KRW'
         AND jan1.reg_dt = '20240101'
         AND today.reg_dt = '20250220'
         ORDER BY acct_no DESC, return_rate_jan1 DESC, return_rate_today DESC
        """
        expected = """
        SELECT jan1.acct_no
         , ( (jan1.total_appr_amt - jan1.deposit_amt) / NULLIF (jan1.deposit_amt, 0) ) * 100 AS return_rate_jan1
         , ( (today.total_appr_amt - today.deposit_amt) / NULLIF (today.deposit_amt, 0) ) * 100 AS return_rate_today
         FROM aicfo_get_all_amt('test_intt', 'test_user', '테스트회사', '20240101', '20240131') jan1
         JOIN aicfo_get_all_amt('test_intt', 'test_user', '테스트회사', '20240101', '20240131') today
         ON jan1.acct_no = today.acct_no
         WHERE com_nm = '비즈플레이'
         AND jan1.view_dv = '증권'
         AND jan1.curr_cd = 'KRW'
         AND jan1.reg_dt = '20240101'
         AND today.reg_dt = '20250220'
         ORDER BY acct_no DESC, return_rate_jan1 DESC, return_rate_today DESC
        """
        
        result = add_view_table(query, self.selected_table, self.view_com, self.user_info, self.view_date, self.flags)
        # 공백 정규화하여 비교
        self.assertEqual(' '.join(result.split()), ' '.join(expected.split()))

if __name__ == '__main__':
    unittest.main()