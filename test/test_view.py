import unittest
from datetime import datetime
from utils.query.view.view_table import ViewTableBuilder
from utils.query.view.extract_date import extract_view_date
from utils.query.view.classify_query import QueryClassifier

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
        print("\n=== Test Setup ===")
        print(f"Original Query:\n{self.base_query}")

    def test_date_extraction_with_subquery(self):
        """날짜 추출 테스트 - 서브쿼리가 있는 경우"""
        print("\n=== Testing Date Extraction ===")
        
        # 쿼리 구조 분석 결과 출력
        classifier = QueryClassifier()
        query_info = classifier.classify_query(self.base_query)
        print(f"\nQuery Structure:")
        print(f"- Has Subquery: {query_info.has_subquery}")
        print(f"- Has Union: {query_info.has_union}")
        print(f"- Table Names: {query_info.table_names}")
        
        # 날짜 추출 실행 및 결과 출력
        from_date, to_date = extract_view_date(self.base_query, self.selected_table, self.flags)
        print(f"\nExtracted Dates:")
        print(f"- From Date: {from_date}")
        print(f"- To Date: {to_date}")
        print(f"- Flags: {self.flags}")
        
        self.assertEqual(from_date, '20241121')
        self.assertEqual(to_date, '20250221')

    def test_view_table_transformation_with_subquery(self):
        """뷰 테이블 변환 테스트 - 서브쿼리가 있는 경우"""
        print("\n=== Testing View Table Transformation ===")
        
        view_date = ('20241121', '20250221')
        print(f"\nInput Parameters:")
        print(f"- Selected Table: {self.selected_table}")
        print(f"- View Company: {self.view_com}")
        print(f"- User Info: {self.user_info}")
        print(f"- View Date: {view_date}")
        
        transformed_query = ViewTableBuilder.transform_query(
            self.base_query,
            self.selected_table,
            self.view_com,
            self.user_info,
            view_date,
            self.flags
        )
        
        print(f"\nTransformed Query:\n{transformed_query}")

        # 변환된 쿼리에서 검증할 부분들
        expected_patterns = [
            "aicfo_get_all_amt('test_intt_id', 'test_user_id', 'test_company', '20241121', '20250221')",
            "aicfo_get_all_trsc('test_intt_id', 'test_user_id', 'test_company', '20241121', '20250221')"
        ]

        print("\nChecking Expected Patterns:")
        for pattern in expected_patterns:
            print(f"- Checking for: {pattern}")
            print(f"  Found: {pattern in transformed_query}")
            self.assertIn(pattern, transformed_query)

if __name__ == '__main__':
    unittest.main(verbosity=2)