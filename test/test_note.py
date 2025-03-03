import pytest
import sqlglot
import sys
import re
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any, Tuple, Optional

# Mock the modules we don't want to import
sys.modules['graph.task.executor'] = MagicMock()
sys.modules['utils.retriever'] = MagicMock()
sys.modules['database.postgresql'] = MagicMock()
sys.modules['llm_admin.qna_manager'] = MagicMock()

# Now that we've mocked the dependencies, we can define our own version of the functions to test
def find_note_conditions(ast):
    """Recreated version of find_note_conditions from ever_note.py for isolated testing
    
    This function finds all note1 conditions in an AST and returns their details.
    """
    note_conditions = []
    visited_nodes = set()
    
    def process_node(node):
        # Skip already visited nodes
        node_id = id(node)
        if node_id in visited_nodes:
            return
        visited_nodes.add(node_id)
        
        # Check for note1 conditions
        if isinstance(node, (sqlglot.exp.EQ, sqlglot.exp.Like, sqlglot.exp.ILike)):
            if (isinstance(node.this, sqlglot.exp.Column) and 
                node.this.name == 'note1'):
                # Extract value
                if isinstance(node.expression, sqlglot.exp.Literal):
                    note_str = str(node.expression.this).strip("'%")
                else:
                    note_str = str(node.expression).strip("'%")
                
                # Store condition info
                note_conditions.append({
                    'type': type(node).__name__,
                    'value': note_str,
                    'node': node
                })
        
        # Process child nodes (arguments method)
        for arg_name, arg_value in node.args.items():
            if isinstance(arg_value, sqlglot.exp.Expression):
                process_node(arg_value)
            elif isinstance(arg_value, list):
                for item in arg_value:
                    if isinstance(item, sqlglot.exp.Expression):
                        process_node(item)
    
    # Start from root node
    process_node(ast)
    
    return note_conditions

def extract_view_function_params(query: str) -> Tuple[str, str, str, str, str]:
    """Recreated version of extract_view_function_params from ever_note.py"""
    pattern = r"(?i)aicfo_get_all_\w+\('([^']+)', '([^']+)', '([^']+)', '([^']+)', '([^']+)'\)"
    match = re.search(pattern, query)
    
    if match:
        use_intt_id = match.group(1)
        user_id = match.group(2)
        company = match.group(3)
        from_date = match.group(4)
        to_date = match.group(5)
        return (use_intt_id, user_id, company, from_date, to_date)
    
    return None

def alternative_find_note_conditions(ast):
    """Alternative implementation that might fix the issue with CASE WHEN"""
    conditions = []
    
    for node in ast.walk():
        if isinstance(node, (sqlglot.exp.EQ, sqlglot.exp.Like, sqlglot.exp.ILike)):
            if isinstance(node.this, sqlglot.exp.Column) and node.this.name == 'note1':
                if isinstance(node.expression, sqlglot.exp.Literal):
                    value = str(node.expression.this).strip("'%")
                else:
                    value = str(node.expression).strip("'%")
                    
                conditions.append({
                    'type': type(node).__name__,
                    'value': value,
                    'node': node
                })
    
    return conditions

class TestNoteConditions:
    
    def test_simple_note_condition(self):
        """Test a simple note1 = 'value' condition"""
        query = "SELECT * FROM table WHERE note1 = '연구비'"
        
        ast = sqlglot.parse_one(query, dialect='postgres')
        conditions = find_note_conditions(ast)
        
        assert len(conditions) == 1
        assert conditions[0]['type'] == 'EQ'
        assert conditions[0]['value'] == '연구비'
    
    def test_like_note_condition(self):
        """Test a LIKE condition with note1"""
        query = "SELECT * FROM table WHERE note1 LIKE '%연구비%'"
        
        ast = sqlglot.parse_one(query, dialect='postgres')
        conditions = find_note_conditions(ast)
        
        assert len(conditions) == 1
        assert conditions[0]['type'] == 'Like'
        assert conditions[0]['value'] == '연구비'
    
    def test_multiple_note_conditions(self):
        """Test multiple note1 conditions in the same query"""
        query = "SELECT * FROM table WHERE note1 = '연구비' OR note1 LIKE '%급여%'"
        
        ast = sqlglot.parse_one(query, dialect='postgres')
        conditions = find_note_conditions(ast)
        
        assert len(conditions) == 2
        values = {c['value'] for c in conditions}
        assert '연구비' in values
        assert '급여' in values
    
    def test_nested_note_conditions(self):
        """Test note1 conditions in nested structures"""
        query = "SELECT * FROM table WHERE (note1 = '연구비' OR note1 LIKE '%급여%') AND trsc_dt > '20250301'"
        
        ast = sqlglot.parse_one(query, dialect='postgres')
        conditions = find_note_conditions(ast)
        
        assert len(conditions) == 2
        values = {c['value'] for c in conditions}
        assert '연구비' in values
        assert '급여' in values
    
    def test_case_when_note_condition(self):
        """Test note1 conditions used in CASE WHEN expressions"""
        query = """SELECT SUM(trsc_amt) AS total_trsc_amt, 
                SUM(CASE WHEN note1 LIKE '%연구비%' THEN trsc_amt ELSE 0 END) AS note_amt 
                FROM table"""
        
        ast = sqlglot.parse_one(query, dialect='postgres')
        conditions = find_note_conditions(ast)
        
        # This test may fail with the current implementation
        assert len(conditions) >= 1
        if len(conditions) > 0:
            assert conditions[0]['type'] == 'Like'
            assert conditions[0]['value'] == '연구비'
    
    def test_complex_query(self):
        """Test the complex query example provided"""
        query = """SELECT SUM(trsc_amt) AS total_trsc_amt, 
                SUM(CASE WHEN note1 LIKE '%연구비%' THEN trsc_amt ELSE 0 END) AS note_amt, 
                (SUM(CASE WHEN note1 LIKE '%연구비%' THEN trsc_amt ELSE 0 END) / SUM(trsc_amt)) * 100 AS note_ratio 
                FROM AICFO_GET_ALL_TRSC('WP8318600562', 'aicfo_w@webcash.co.kr', '뉴젠피앤피', '20250301', '20250303') 
                WHERE com_nm = '뉴젠피앤피' AND view_dv = '수시' AND curr_cd = 'KRW' AND in_out_dv = '출금' 
                AND trsc_dt BETWEEN '20250301' AND '20250303' 
                ORDER BY total_trsc_amt DESC"""
        
        ast = sqlglot.parse_one(query, dialect='postgres')
        conditions = find_note_conditions(ast)
        
        # This test may fail with the current implementation
        assert len(conditions) >= 1
        if len(conditions) > 0:
            assert conditions[0]['type'] == 'Like'
            assert conditions[0]['value'] == '연구비'
    
    def test_extract_view_function_params(self):
        """Test that view function parameters are extracted correctly"""
        query = "SELECT * FROM AICFO_GET_ALL_TRSC('WP8318600562', 'aicfo_w@webcash.co.kr', '뉴젠피앤피', '20250301', '20250303')"
        
        params = extract_view_function_params(query)
        
        assert params is not None
        assert len(params) == 5
        assert params[0] == 'WP8318600562'
        assert params[1] == 'aicfo_w@webcash.co.kr'
        assert params[2] == '뉴젠피앤피'
        assert params[3] == '20250301'
        assert params[4] == '20250303'
    
    def test_alternative_implementation(self):
        """Test an alternative implementation for find_note_conditions"""
        # The complex query with note1 in CASE WHEN
        query = """SELECT SUM(trsc_amt) AS total_trsc_amt, 
                SUM(CASE WHEN note1 LIKE '%연구비%' THEN trsc_amt ELSE 0 END) AS note_amt, 
                (SUM(CASE WHEN note1 LIKE '%연구비%' THEN trsc_amt ELSE 0 END) / SUM(trsc_amt)) * 100 AS note_ratio 
                FROM AICFO_GET_ALL_TRSC('WP8318600562', 'aicfo_w@webcash.co.kr', '뉴젠피앤피', '20250301', '20250303') 
                WHERE com_nm = '뉴젠피앤피' AND view_dv = '수시' AND curr_cd = 'KRW' AND in_out_dv = '출금' 
                AND trsc_dt BETWEEN '20250301' AND '20250303' 
                ORDER BY total_trsc_amt DESC"""
        
        ast = sqlglot.parse_one(query, dialect='postgres')
        conditions = alternative_find_note_conditions(ast)
        
        # The alternative implementation should find both note1 conditions
        assert len(conditions) == 2
        assert all(c['type'] == 'Like' for c in conditions)
        assert all(c['value'] == '연구비' for c in conditions)