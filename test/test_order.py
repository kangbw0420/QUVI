import unittest
import sys
import os

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.query.orderby import add_order_by, has_order_by

class TestOrderBy(unittest.TestCase):
    
    def test_simple_query(self):
        """Test adding ORDER BY to a simple query"""
        query = "SELECT * FROM mytable"
        result = add_order_by(query, "amt")
        print(f"1. {result}")
        self.assertEqual(result, "SELECT * FROM mytable ORDER BY reg_dt DESC;")
    
    def test_query_with_where(self):
        """Test adding ORDER BY to a query with WHERE clause"""
        query = "SELECT * FROM mytable WHERE col1 = 'value'"
        result = add_order_by(query, "trsc")
        print(f"2. {result}")
        self.assertEqual(result, "SELECT * FROM mytable WHERE col1 = 'value' ORDER BY trsc_dt DESC;")
    
    def test_query_with_existing_order_by(self):
        """Test that existing ORDER BY clauses are preserved"""
        query = "SELECT * FROM mytable ORDER BY custom_col ASC;"
        result = add_order_by(query, "trsc")
        print(f"3. {result}")
        self.assertEqual(result, query)
    
    def test_group_by_query(self):
        """Test query with GROUP BY clause"""
        query = "SELECT col1, SUM(col2) AS total FROM mytable GROUP BY col1"
        result = add_order_by(query, "trsc")
        print(f"4. {result}")
        self.assertEqual(result, "SELECT col1, SUM(col2) AS total FROM mytable GROUP BY col1 ORDER BY total DESC;")
    
    def test_has_order_by(self):
        """Test detection of ORDER BY clause"""
        self.assertTrue(has_order_by("SELECT * FROM mytable ORDER BY col1"))
        self.assertFalse(has_order_by("SELECT * FROM mytable"))
        self.assertTrue(has_order_by("SELECT * FROM mytable ORDER BY col1 -- with comment"))
    
    def test_subquery_with_external_order_by(self):
        """Test handling of subqueries with external ORDER BY"""
        query = """
        SELECT COUNT(*) as cnt FROM (
            SELECT trsc_dt, 
                   SUM(CASE WHEN in_out_dv = '입금' THEN trsc_amt ELSE 0 END) as total_in,
                   SUM(CASE WHEN in_out_dv = '출금' THEN trsc_amt ELSE 0 END) as total_out
            FROM mytable
            WHERE view_dv = '수시' AND curr_cd = 'krw'
            GROUP BY trsc_dt
            HAVING total_in > total_out
        ) subq ORDER BY total_in DESC
        """
        result = add_order_by(query, "trsc")
        print(f"5. {result}")
        self.assertNotIn("ORDER BY total_in", result)
        self.assertTrue("ORDER BY cnt DESC" in result or "ORDER BY 1 DESC" in result)
    
    def test_trsc_table_default_order(self):
        """Test default ordering for trsc table"""
        query = "SELECT trsc_dt, note1, trsc_amt FROM mytable"
        result = add_order_by(query, "trsc")
        print(f"6. {result}")
        self.assertEqual(result, "SELECT trsc_dt, note1, trsc_amt FROM mytable ORDER BY trsc_dt DESC;")
    
    def test_amt_table_default_order(self):
        """Test default ordering for amt table"""
        query = "SELECT reg_dt, acct_bal_amt FROM mytable"
        result = add_order_by(query, "amt")
        print(f"7. {result}")
        self.assertEqual(result, "SELECT reg_dt, acct_bal_amt FROM mytable ORDER BY reg_dt DESC;")
    
    def test_complex_nested_query(self):
        """Test handling of complex nested queries with ORDER BY"""
        query = """
        SELECT a.* FROM (
            SELECT col1, SUM(col2) AS total 
            FROM (
                SELECT * FROM inner_table
                WHERE condition = 'value'
            ) t1
            GROUP BY col1
        ) a
        """
        result = add_order_by(query, "trsc")
        print(f"8. {result}")
        self.assertTrue("ORDER BY" in result)
        self.assertTrue("col1 DESC" in result or "total DESC" in result or "1 DESC" in result)

    def test_query_with_date_functions(self):
        """Test query with date manipulation functions"""
        query = """
        SELECT TO_CHAR(DATE_TRUNC('month', trsc_dt::timestamp), 'yyyymm') AS trsc_month, 
               SUM(trsc_amt) AS total_trsc_amt 
        FROM mytable
        WHERE com_nm = '비즈플레이'
        GROUP BY trsc_month
        """
        result = add_order_by(query, "trsc")
        print(f"9. {result}")
        self.assertTrue("ORDER BY trsc_month DESC" in result or "ORDER BY total_trsc_amt DESC" in result)
    
    def test_query_with_aggregate_function(self):
        """Test query with aggregate functions"""
        query = "SELECT COUNT(*) as count, AVG(col) as average FROM mytable"
        result = add_order_by(query, "trsc")
        print(f"10. {result}")
        self.assertTrue("ORDER BY count DESC" in result or "ORDER BY 1 DESC" in result)
    
    def test_malformed_order_by(self):
        """Test detection and handling of malformed ORDER BY clauses"""
        query = """
        SELECT TO_CHAR(DATE_TRUNC('month', trsc_dt::timestamp), 'yyyymm') AS trsc_month, 
               SUM(trsc_amt) AS total_trsc_amt 
        FROM mytable
        GROUP BY trsc_month
        ORDER BY TO_CHAR(DATE_TRUNC('month desc, trsc_dt::timestamp) desc, trsc_month DESC
        """
        # Since add_order_by should only add ORDER BY if it's not already present,
        # and not try to fix malformed ones, the result should be the same as input
        result = add_order_by(query, "trsc")
        print(f"11. {result}")
        self.assertEqual(result.strip(), query.strip() + ";")

if __name__ == '__main__':
    unittest.main()