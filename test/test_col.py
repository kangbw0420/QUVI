import unittest
from utils.extract_data_info import extract_col_from_query

import unittest
import sys
import os

# Add the parent directory to sys.path to import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.extract_data_info import extract_col_from_query, extract_col_from_dict

class TestColumnExtraction(unittest.TestCase):
    
    def test_simple_select(self):
        query = "SELECT col1, col2, col3 FROM table"
        expected = ["col1", "col2", "col3"]
        self.assertEqual(extract_col_from_query(query), expected)
        
    def test_select_star(self):
        query = "SELECT * FROM table"
        expected = ["*"]
        self.assertEqual(extract_col_from_query(query), expected)
        
    def test_aliased_columns(self):
        query = "SELECT col1 AS alias1, col2 AS alias2 FROM table"
        expected = ["alias1", "alias2"]
        self.assertEqual(extract_col_from_query(query), expected)
        
    def test_quoted_aliases(self):
        query = 'SELECT col1 AS "Alias One", col2 AS "Alias Two" FROM table'
        expected = ["Alias One", "Alias Two"]
        self.assertEqual(extract_col_from_query(query), expected)
        
    def test_table_prefixed_columns(self):
        query = "SELECT t1.col1, t2.col2 FROM table1 t1 JOIN table2 t2"
        expected = ["col1", "col2"]
        self.assertEqual(extract_col_from_query(query), expected)
        
    def test_functions(self):
        query = "SELECT COUNT(*) AS count, AVG(price) AS average FROM products"
        expected = ["count", "average"]
        self.assertEqual(extract_col_from_query(query), expected)
        
    def test_complex_expressions(self):
        query = "SELECT TO_CHAR(DATE_TRUNC('month', trsc_dt::timestamp), 'YYYYMM') AS trsc_month, SUM(trsc_amt) AS total_amt FROM transactions"
        expected = ["trsc_month", "total_amt"]
        self.assertEqual(extract_col_from_query(query), expected)
        
    def test_complex_without_alias(self):
        query = "SELECT TO_CHAR(DATE_TRUNC('month', trsc_dt::timestamp), 'YYYYMM'), SUM(trsc_amt) FROM transactions"
        expected = ["TO_CHAR", "SUM"]
        self.assertEqual(extract_col_from_query(query), expected)
        
    def test_nested_functions(self):
        query = "SELECT ROUND(AVG(COALESCE(price, 0)), 2) AS avg_price FROM products"
        expected = ["avg_price"]
        self.assertEqual(extract_col_from_query(query), expected)
        
    def test_case_expressions(self):
        query = """
        SELECT
            CASE
                WHEN price > 100 THEN 'Expensive'
                ELSE 'Cheap'
            END AS price_category,
            COUNT(*) AS product_count
        FROM products
        GROUP BY price_category
        """
        expected = ["price_category", "product_count"]
        self.assertEqual(extract_col_from_query(query), expected)
        
    def test_subqueries(self):
        query = """
        SELECT
            a.col1,
            (SELECT MAX(price) FROM products) AS max_price
        FROM
            table a
        """
        expected = ["col1", "max_price"]
        self.assertEqual(extract_col_from_query(query), expected)
        
    def test_window_functions(self):
        query = """
        SELECT
            name,
            price,
            RANK() OVER (PARTITION BY category ORDER BY price DESC) AS price_rank
        FROM products
        """
        expected = ["name", "price", "price_rank"]
        self.assertEqual(extract_col_from_query(query), expected)
        
    def test_complex_real_query(self):
        query = """
        SELECT
            TO_CHAR(DATE_TRUNC('month', trsc_dt::timestamp), 'YYYYMM') AS trsc_month,
            SUM(trsc_amt) AS total_trsc_amt
        FROM
            aicfo_get_all_trsc
        WHERE
            view_dv = '수시' AND
            curr_cd = 'KRW' AND
            trsc_dt BETWEEN '20250101' AND '20250218' AND
            in_out_dv = '입금'
        GROUP BY
            trsc_month
        ORDER BY
            trsc_month DESC
        """
        expected = ["trsc_month", "total_trsc_amt"]
        self.assertEqual(extract_col_from_query(query), expected)
        
    def test_malformed_query(self):
        query = "This is not a valid SQL query"
        expected = []
        self.assertEqual(extract_col_from_query(query), expected)
        
    def test_extract_from_dict(self):
        result = [
            {"col1": 1, "col2": "value1", "col3": True},
            {"col1": 2, "col2": "value2", "col3": False}
        ]
        expected = ["col1", "col2", "col3"]
        self.assertEqual(extract_col_from_dict(result), expected)
        
    def test_extract_from_empty_dict(self):
        result = []
        with self.assertRaises(ValueError):
            extract_col_from_dict(result)
            
    def test_no_select_statement(self):
        query = "INSERT INTO table (col1, col2) VALUES (1, 2)"
        expected = []
        self.assertEqual(extract_col_from_query(query), expected)
        
    def test_comments_in_query(self):
        query = """
        -- This is a comment
        SELECT 
            col1, -- Column 1
            col2  /* Column 2 */
        FROM table
        """
        expected = ["col1", "col2"]
        self.assertEqual(extract_col_from_query(query), expected)
        
    def test_tricky_string_literals(self):
        query = """
        SELECT
            name,
            'Value with , comma' AS description,
            "Column with "" quotes" AS quoted_col
        FROM table
        """
        expected = ["name", "description", "quoted_col"]
        self.assertEqual(extract_col_from_query(query), expected)

if __name__ == '__main__':
    unittest.main()