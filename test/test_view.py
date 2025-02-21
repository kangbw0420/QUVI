import unittest
from datetime import datetime
from utils.query.view.view_table import ViewTableBuilder
from utils.query.view.extract_date import extract_view_date

class TestViewTableTransformation(unittest.TestCase):
    def setUp(self):
        self.base_query = """
            SELECT DISTINCT acct_no, bank_nm 
            FROM aicfo_get_all_amt 
            WHERE view_dv = '수시' AND curr_cd = 'KRW' AND reg_dt = '20250221' 
            AND acct_no NOT IN (
                SELECT DISTINCT acct_no 
                FROM aicfo_get_all_trsc 
                WHERE view_dv = '수시' AND curr_cd = 'KRW' AND trsc_dt > '20241121'
            )
        """
        self.selected_table = 'amt'
        self.view_com = 'test_company'
        self.user_info = ('test_intt_id', 'test_user_id')
        self.flags = {
            'future_date': False,
            'past_date': False
        }

    def test_date_extraction_with_subquery(self):
        """날짜 추출 테스트 - 서브쿼리가 있는 경우"""
        from_date, to_date = extract_view_date(self.base_query, self.selected_table, self.flags)
        
        # 메인 쿼리와 서브쿼리의 날짜 중 가장 이른 날짜가 from_date가 되어야 함
        self.assertEqual(from_date, '20241121')
        # 메인 쿼리와 서브쿼리의 날짜 중 가장 늦은 날짜가 to_date가 되어야 함
        self.assertEqual(to_date, '20250221')

    def test_view_table_transformation_with_subquery(self):
        """뷰 테이블 변환 테스트 - 서브쿼리가 있는 경우"""
        view_date = ('20241121', '20250221')
        transformed_query = ViewTableBuilder.transform_query(
            self.base_query,
            self.selected_table,
            self.view_com,
            self.user_info,
            view_date,
            self.flags
        )

        # 변환된 쿼리에서 검증할 부분들
        expected_patterns = [
            # 메인 쿼리의 view function 호출
            "aicfo_get_all_amt('test_intt_id', 'test_user_id', 'test_company', '20241121', '20250221')",
            # 서브쿼리의 view function 호출
            "aicfo_get_all_trsc('test_intt_id', 'test_user_id', 'test_company', '20241121', '20250221')"
        ]

        for pattern in expected_patterns:
            self.assertIn(pattern, transformed_query)

if __name__ == '__main__':
    unittest.main()