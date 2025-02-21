import unittest
from utils.query.view.view_table import ViewTableTransformer

class TestViewTable(unittest.TestCase):
    def setUp(self):
        self.selected_table = "amt"
        self.user_info = ("test_user", "test_intt_id")
        self.view_com = "테스트기업"
        self.flags = {
            "future_date": False,
            "past_date": False
        }

        self.transformer = ViewTableTransformer(
            selected_table=self.selected_table,
            user_info=self.user_info,
            view_com=self.view_com,
            flags=self.flags
        )

    def test_subquery_with_different_dates(self):
        query = """
        SELECT bank_nm, acct_dv, acct_no, acct_bal_amt, real_amt, acct_bal_upd_dtm 
        FROM aicfo_get_all_amt 
        WHERE view_dv = '수시' AND curr_cd = 'KRW' AND reg_dt = '20250221' 
        AND acct_no NOT IN (
            SELECT DISTINCT acct_no 
            FROM aicfo_get_all_trsc 
            WHERE view_dv = '수시' AND curr_cd = 'KRW' AND trsc_dt > '20241121'
        )
        """
        _, date_ranges = self.transformer.transform_query(query)
        
        self.assertIn("main", date_ranges)
        self.assertEqual(date_ranges["main"], ("20250221", "20250221"))
        
        subquery_key = next((k for k in date_ranges.keys() if k.startswith("subquery")), None)
        self.assertIsNotNone(subquery_key, "서브쿼리 날짜 정보가 없습니다")
        
        self.assertEqual(date_ranges[subquery_key][0], ("20241121", "20250221"))

if __name__ == "__main__":
    unittest.main()
    

    # def test_union_with_different_dates(self):
    #     """UNION이 있고 각각 다른 날짜 조건이 있는 쿼리 테스트"""
    #     # UNION이 있는 복잡한 쿼리
    #     query = """
    #     SELECT bank_nm, acct_no, reg_dt, acct_bal_amt 
    #     FROM aicfo_get_all_amt 
    #     WHERE reg_dt = '20250221' 
    #     UNION 
    #     SELECT bank_nm, acct_no, trsc_dt as reg_dt, trsc_amt as acct_bal_amt 
    #     FROM aicfo_get_all_trsc 
    #     WHERE trsc_dt = '20250120'
    #     """
        
    #     # 변환 및 날짜 정보 추출
    #     _, date_ranges = self.transformer.transform_query(query)
        
    #     # 검증
    #     self.assertIn("left_union", date_ranges)
    #     self.assertIn("right_union", date_ranges)
        
    #     # 왼쪽과 오른쪽 유니온의 날짜 정보 각각 검증
    #     self.assertEqual(date_ranges["left_union"], ("20250221", "20250221"))
    #     self.assertEqual(date_ranges["right_union"], ("20250120", "20250120"))
    
    # def test_multiple_subqueries(self):
    #     query = """
    #     SELECT bank_nm, acct_no, acct_bal_amt 
    #     FROM aicfo_get_all_amt 
    #     WHERE reg_dt = '20250221' 
    #     AND acct_no IN (
    #         SELECT acct_no 
    #         FROM aicfo_get_all_trsc 
    #         WHERE trsc_dt = '20240301' 
    #         AND trsc_amt > (
    #             SELECT AVG(trsc_amt) 
    #             FROM aicfo_get_all_trsc 
    #             WHERE trsc_dt BETWEEN '20250101' AND '20250221'
    #         )
    #     )
    #     """
    #     _, date_ranges = self.transformer.transform_query(query)
        
    #     self.assertIn("main", date_ranges)
    #     self.assertEqual(date_ranges["main"], ("20250221", "20250221"))
    #     subquery_key = next((k for k in date_ranges.keys() if k.startswith("subquery")), None)
    #     self.assertEqual(date_ranges[subquery_key][0], ("20250101", "20250221"))
    #     self.assertEqual(date_ranges[subquery_key][1], ("20250101", "20250221"))
        
    #     subquery_keys = [k for k in date_ranges.keys() if k.startswith("subquery")]
    #     self.assertGreaterEqual(len(subquery_keys), 2, "적어도 2개 이상의 서브쿼리 날짜 정보가 필요합니다")