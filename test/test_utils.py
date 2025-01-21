import unittest
from utils.check_com import check_com_nm
from utils.stats import analyze_data

class TestDataProcessing(unittest.TestCase):
    def setUp(self):
        # 테스트 데이터 설정
        self.test_data = [
            {
                "view_dv": "입출금",
                "com_nm": "삼성전자",
                "bank_nm": "신한은행",
                "acct_no": "123-456-789",
                "curr_cd": "KRW",
                "seq_no": "001",
                "trsc_dt": "20250101",
                "trsc_tm": "090000",
                "in_out_dv": "출금",
                "trsc_amt": 1000000,
                "trsc_bal": 9000000,
                "note1": "급여지급"
            },
            {
                "view_dv": "입출금",
                "com_nm": "삼성전자",
                "bank_nm": "신한은행",
                "acct_no": "123-456-789",
                "curr_cd": "USD",
                "seq_no": "002",
                "trsc_dt": "20250101",
                "trsc_tm": "100000",
                "in_out_dv": "입금",
                "trsc_amt": 5000,
                "trsc_bal": 15000,
                "note1": "해외송금"
            },
            {
                "view_dv": "입출금",
                "com_nm": "삼성전자",
                "bank_nm": "우리은행",
                "acct_no": "987-654-321",
                "curr_cd": "KRW",
                "seq_no": "003",
                "trsc_dt": "20250101",
                "trsc_tm": "110000",
                "in_out_dv": "출금",
                "trsc_amt": 2000000,
                "trsc_bal": 7000000,
                "note1": "물품구매"
            },
            {
                "view_dv": "입출금",
                "com_nm": "삼성전자",
                "bank_nm": "우리은행",
                "acct_no": "987-654-321",
                "curr_cd": "KRW",
                "seq_no": "004",
                "trsc_dt": "20250101",
                "trsc_tm": "120000",
                "in_out_dv": "입금",
                "trsc_amt": 3000000,
                "trsc_bal": 10000000,
                "note1": "매출입금"
            },
            {
                "view_dv": "입출금",
                "com_nm": "현대자동차",
                "bank_nm": "국민은행",
                "acct_no": "111-222-333",
                "curr_cd": "KRW",
                "seq_no": "001",
                "trsc_dt": "20250101",
                "trsc_tm": "090000",
                "in_out_dv": "출금",
                "trsc_amt": 500000,
                "trsc_bal": 4500000,
                "note1": "운영비"
            },
            {
                "view_dv": "입출금",
                "com_nm": "현대자동차",
                "bank_nm": "국민은행",
                "acct_no": "111-222-333",
                "curr_cd": "EUR",
                "seq_no": "002",
                "trsc_dt": "20250101",
                "trsc_tm": "100000",
                "in_out_dv": "입금",
                "trsc_amt": 3000,
                "trsc_bal": 8000,
                "note1": "수출대금"
            },
            {
                "view_dv": "입출금",
                "com_nm": "현대자동차",
                "bank_nm": "하나은행",
                "acct_no": "444-555-666",
                "curr_cd": "KRW",
                "seq_no": "003",
                "trsc_dt": "20250101",
                "trsc_tm": "110000",
                "in_out_dv": "출금",
                "trsc_amt": 1500000,
                "trsc_bal": 3000000,
                "note1": "임대료"
            },
            {
                "view_dv": "입출금",
                "com_nm": "현대자동차",
                "bank_nm": "하나은행",
                "acct_no": "444-555-666",
                "curr_cd": "KRW",
                "seq_no": "004",
                "trsc_dt": "20250101",
                "trsc_tm": "120000",
                "in_out_dv": "입금",
                "trsc_amt": 2000000,
                "trsc_bal": 5000000,
                "note1": "대금입금"
            }
        ]

    def test_check_com_nm_with_multiple_companies(self):
        """여러 회사가 있는 경우 check_com_nm 테스트"""
        result = check_com_nm(self.test_data)
        
        # 결과가 딕셔너리인지 확인
        self.assertIsInstance(result, dict)
        
        # 예상되는 회사들이 키로 존재하는지 확인
        self.assertIn("삼성전자", result)
        self.assertIn("현대자동차", result)
        
        # 각 회사별 데이터 수 확인
        self.assertEqual(len(result["삼성전자"]), 4)
        self.assertEqual(len(result["현대자동차"]), 4)
        
        # 각 회사의 첫 번째 데이터가 올바른지 확인
        self.assertEqual(result["삼성전자"][0]["bank_nm"], "신한은행")
        self.assertEqual(result["현대자동차"][0]["bank_nm"], "국민은행")

    def test_check_com_nm_with_single_company(self):
        """단일 회사만 있는 경우 check_com_nm 테스트"""
        # 삼성전자 데이터만 선택
        single_company_data = [d for d in self.test_data if d["com_nm"] == "삼성전자"]
        result = check_com_nm(single_company_data)
        
        # 결과가 리스트인지 확인
        self.assertIsInstance(result, list)
        
        # 데이터 수 확인
        self.assertEqual(len(result), 4)
        
        # 모든 데이터가 같은 회사인지 확인
        self.assertTrue(all(d["com_nm"] == "삼성전자" for d in result))

    def test_analyze_data_with_multiple_companies(self):
        """회사별로 구조화된 데이터에 대한 analyze_data 테스트"""
        # 먼저 데이터를 회사별로 구조화
        structured_data = check_com_nm(self.test_data)
        result = analyze_data(structured_data, "trsc")
        
        # 결과가 리스트인지 확인
        self.assertIsInstance(result, list)
        
        # 각 회사별 분석 결과가 포함되어 있는지 확인
        company_results = "\n".join(result)
        self.assertIn("삼성전자", company_results)
        self.assertIn("현대자동차", company_results)
        
        # 통화별 통계가 포함되어 있는지 확인
        self.assertIn("KRW", company_results)
        self.assertIn("USD", company_results)
        self.assertIn("EUR", company_results)

    def test_analyze_data_with_single_company(self):
        """단일 회사 데이터에 대한 analyze_data 테스트"""
        # 삼성전자 데이터만 선택
        single_company_data = [d for d in self.test_data if d["com_nm"] == "삼성전자"]
        result = analyze_data(single_company_data, "trsc")
        
        # 결과가 리스트인지 확인
        self.assertIsInstance(result, list)
        
        # 결과를 문자열로 결합
        result_str = "\n".join(result)
        
        # 필요한 정보가 포함되어 있는지 확인
        self.assertIn("trsc_amt", result_str)
        self.assertIn("KRW", result_str)
        self.assertIn("USD", result_str)

if __name__ == '__main__':
    unittest.main()