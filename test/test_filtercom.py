import unittest
from utils.filter_com import filter_com

class TestFilterCom(unittest.TestCase):
    def setUp(self):
        self.main_com = "웹케시"
        self.sub_coms = ["비즈플레이", "웹케시글로벌", "위플렉스"]

    def assert_sql_equal(self, result: str, expected: str):
        """SQL 쿼리 비교 - 공백과 줄바꿈을 정규화하여 비교"""
        def normalize(sql: str) -> str:
            # 여러 공백과 줄바꿈을 단일 공백으로 변환
            return ' '.join(sql.split())
        
        normalized_result = normalize(result)
        normalized_expected = normalize(expected)
        self.assertEqual(normalized_result, normalized_expected)

    def print_test_case(self, test_name: str, input_query: str, expected: str, actual: str):
        print("\n" + "="*80)
        print(f"Test Case: {test_name}")
        print("-"*80)
        print(f"Input Query:\n{input_query}")
        print("-"*80)
        print(f"Expected Output:\n{expected}")
        print("-"*80)
        print(f"Actual Output:\n{actual}")
        print("="*80)

    def test_no_com_nm_condition(self):
        """회사명 조건이 없는 경우 테스트"""
        print("\n[Testing queries without company name condition]")
        
        # WHERE 절이 있는 경우
        query1 = "SELECT * FROM aicfo_get_all_amt WHERE view_dv = '전체'"
        expected1 = "SELECT * FROM aicfo_get_all_amt WHERE com_nm = '웹케시' AND view_dv = '전체'"
        result1 = filter_com(query1, self.main_com, self.sub_coms)
        self.print_test_case("WHERE clause exists", query1, expected1, result1)
        self.assert_sql_equal(result1, expected1)

        # WHERE 절이 없는 경우
        query2 = "SELECT * FROM aicfo_get_all_amt"
        expected2 = "SELECT * FROM aicfo_get_all_amt WHERE com_nm = '웹케시'"
        result2 = filter_com(query2, self.main_com, self.sub_coms)
        self.print_test_case("No WHERE clause", query2, expected2, result2)
        self.assert_sql_equal(result2, expected2)

        # ORDER BY가 있는 경우
        query3 = "SELECT * FROM aicfo_get_all_amt ORDER BY reg_dt DESC"
        expected3 = "SELECT * FROM aicfo_get_all_amt WHERE com_nm = '웹케시' ORDER BY reg_dt DESC"
        result3 = filter_com(query3, self.main_com, self.sub_coms)
        self.print_test_case("With ORDER BY", query3, expected3, result3)
        self.assert_sql_equal(result3, expected3)

    def test_single_com_nm_condition(self):
        """단일 회사명 조건이 있는 경우 테스트"""
        print("\n[Testing queries with single company name condition]")
        
        # 단일 회사명이 지정된 경우
        query1 = "SELECT * FROM aicfo_get_all_amt WHERE com_nm = '웹케시하위'"
        result1 = filter_com(query1, self.main_com, self.sub_coms)
        self.print_test_case("Single company name", query1, query1, result1)
        self.assert_sql_equal(result1, query1)

        # 다른 조건과 함께 있는 경우
        query2 = "SELECT * FROM aicfo_get_all_amt WHERE view_dv = '전체' AND com_nm = '웹케시하위'"
        result2 = filter_com(query2, self.main_com, self.sub_coms)
        self.print_test_case("Single company name with other conditions", query2, query2, result2)
        self.assert_sql_equal(result2, query2)

    def test_in_clause_with_main_com(self):
        """IN 절에 main_com이 포함된 경우 테스트"""
        print("\n[Testing IN clause with main company]")
        
        # main_com이 포함된 IN 절
        query1 = "SELECT * FROM aicfo_get_all_amt WHERE com_nm IN ('웹케시', '비즈플레이', '웹케시글로벌')"
        expected1 = "SELECT * FROM aicfo_get_all_amt WHERE com_nm = '웹케시'"
        result1 = filter_com(query1, self.main_com, self.sub_coms)
        self.print_test_case("IN clause with main company", query1, expected1, result1)
        self.assert_sql_equal(result1, expected1)

        # 다른 조건과 함께 있는 경우
        query2 = """
            SELECT * FROM aicfo_get_all_amt 
            WHERE view_dv = '전체' 
            AND com_nm IN ('웹케시', '비즈플레이', '웹케시글로벌')
            AND reg_dt = '20240101'
        """
        expected2 = """
            SELECT * FROM aicfo_get_all_amt 
            WHERE view_dv = '전체' 
            AND com_nm = '웹케시'
            AND reg_dt = '20240101'
        """
        result2 = filter_com(query2, self.main_com, self.sub_coms)
        self.print_test_case("IN clause with main company and other conditions", query2, expected2, result2)
        self.assert_sql_equal(result2, expected2)

    def test_in_clause_without_main_com(self):
        """IN 절에 main_com이 포함되지 않은 경우 테스트"""
        print("\n[Testing IN clause without main company]")
        
        # main_com이 없는 IN 절
        query1 = "SELECT * FROM aicfo_get_all_amt WHERE com_nm IN ('웹케시하위', '비즈플레이', '웹케시글로벌')"
        expected1 = "SELECT * FROM aicfo_get_all_amt WHERE com_nm = '웹케시하위'"
        result1 = filter_com(query1, self.main_com, self.sub_coms)
        self.print_test_case("IN clause without main company", query1, expected1, result1)
        self.assert_sql_equal(result1, expected1)

        # 다른 조건과 함께 있는 경우
        query2 = """
            SELECT * FROM aicfo_get_all_amt 
            WHERE com_nm IN ('웹케시하위', '비즈플레이', '웹케시글로벌')
            AND view_dv = '전체'
        """
        expected2 = """
            SELECT * FROM aicfo_get_all_amt 
            WHERE com_nm = '웹케시하위'
            AND view_dv = '전체'
        """
        result2 = filter_com(query2, self.main_com, self.sub_coms)
        self.print_test_case("IN clause without main company and other conditions", query2, expected2, result2)
        self.assert_sql_equal(result2, expected2)

    def test_complex_queries(self):
        """복잡한 쿼리 케이스 테스트"""
        print("\n[Testing complex queries]")
        
        # 서브쿼리가 있는 경우
        query1 = """
            SELECT * FROM aicfo_get_all_amt 
            WHERE view_dv IN (
                SELECT DISTINCT view_dv 
                FROM aicfo_get_all_amt 
                WHERE reg_dt = '20240101'
            )
        """
        expected1 = """
            SELECT * FROM aicfo_get_all_amt 
            WHERE com_nm = '웹케시' AND view_dv IN (
                SELECT DISTINCT view_dv 
                FROM aicfo_get_all_amt 
                WHERE reg_dt = '20240101'
            )
        """
        result1 = filter_com(query1, self.main_com, self.sub_coms)
        self.print_test_case("Query with subquery", query1, expected1, result1)
        self.assert_sql_equal(result1, expected1)

        # UNION이 있는 경우
        query2 = """
            SELECT * FROM aicfo_get_all_amt WHERE view_dv = '전체'
            UNION
            SELECT * FROM aicfo_get_all_amt WHERE view_dv = '수시'
        """
        expected2 = """
            SELECT * FROM aicfo_get_all_amt WHERE com_nm = '웹케시' AND view_dv = '전체'
            UNION
            SELECT * FROM aicfo_get_all_amt WHERE com_nm = '웹케시' AND view_dv = '수시'
        """
        result2 = filter_com(query2, self.main_com, self.sub_coms)
        self.print_test_case("Query with UNION", query2, expected2, result2)
        self.assert_sql_equal(result2, expected2)

if __name__ == '__main__':
    unittest.main(verbosity=2)