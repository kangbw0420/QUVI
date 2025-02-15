import re
from typing import Optional
import unittest

class NameModifier:
    def __init__(self, name_type: str, name_mappings: dict):
        self.name_type = name_type
        self.column_name = f"{name_type}_nm"
        self.name_mappings = name_mappings

    def _find_all_patterns(self, query: str) -> list:
        """Find all name patterns in the query"""
        patterns = []
        
        # Equal pattern: column_nm = 'value'
        equal_pattern = f"{self.column_name}\\s*=\\s*'([^']*)'+"
        for match in re.finditer(equal_pattern, query, re.IGNORECASE):
            patterns.append((
                match.group(1),  # name
                '=',            # operator
                match.group(0)  # full match
            ))
            
        # IN pattern: column_nm IN ('value1', 'value2')
        in_pattern = f"{self.column_name}\\s+IN\\s*\\(([^)]*)\\)"
        for match in re.finditer(in_pattern, query, re.IGNORECASE):
            patterns.append((
                match.group(1),  # values string
                'IN',           # operator
                match.group(0)  # full match
            ))
                
        # LIKE pattern: column_nm LIKE '%value%'
        like_pattern = f"{self.column_name}\\s+LIKE\\s+'%([^%]+)%'"
        for match in re.finditer(like_pattern, query, re.IGNORECASE):
            patterns.append((
                match.group(1),  # name
                'LIKE',         # operator
                match.group(0)  # full match
            ))
            
        return patterns

    def modify_query(self, query: str) -> str:
        patterns = self._find_all_patterns(query)
        modified_query = query
        
        for names_str, operator, full_match in patterns:
            if operator == '=':
                official_name = self.name_mappings.get(names_str)
                if official_name:
                    new_condition = f"{self.column_name} = '{official_name}'"
                    modified_query = modified_query.replace(full_match, new_condition)
            elif operator == 'IN':
                # Split the values and process each one
                values = [v.strip().strip("'\"") for v in names_str.split(',')]
                new_values = []
                for value in values:
                    official_name = self.name_mappings.get(value)
                    new_values.append(f"'{official_name}'" if official_name else f"'{value}'")
                new_condition = f"{self.column_name} IN ({', '.join(new_values)})"
                modified_query = modified_query.replace(full_match, new_condition)
            else:  # LIKE
                official_name = self.name_mappings.get(names_str)
                if official_name:
                    new_condition = f"{self.column_name} LIKE '%{official_name}%'"
                    modified_query = modified_query.replace(full_match, new_condition)
        
        return modified_query

class TestNameModifier(unittest.TestCase):
    def setUp(self):
        # Test data
        self.bank_mappings = {
            '카뱅': '카카오뱅크',
            '농협은행': '농협',
            '국민': 'KB국민은행',
            '신한': '신한은행',
            '우리뱅크': '우리은행'
        }
        
        self.stock_mappings = {
            '삼성': '삼성전자',
            'SK하닉': 'SK하이닉스',
            'LG디플': 'LG디스플레이',
            '셀트': '셀트리온'
        }
        
        self.bank_modifier = NameModifier('bank', self.bank_mappings)
        self.stock_modifier = NameModifier('stock', self.stock_mappings)

    def test_find_patterns(self):
        """Test pattern finding functionality"""
        query = """
        SELECT * FROM table 
        WHERE bank_nm = '카뱅'
        AND bank_nm IN ('신한', '우리뱅크')
        AND (bank_nm LIKE '%농협은행%' OR bank_nm LIKE '%국민%')
        """
        
        patterns = self.bank_modifier._find_all_patterns(query)
        
        # Should find exactly 4 patterns
        self.assertEqual(len(patterns), 4)
        
        # Verify each pattern type is found
        pattern_types = [p[1] for p in patterns]
        pattern_counts = {
            '=': 0,
            'IN': 0,
            'LIKE': 0
        }
        for ptype in pattern_types:
            pattern_counts[ptype] += 1
        
        self.assertEqual(pattern_counts['='], 1)
        self.assertEqual(pattern_counts['IN'], 1)
        self.assertEqual(pattern_counts['LIKE'], 2)
        
        # Extract and verify all names
        names = []
        for value, op_type, _ in patterns:
            if op_type == 'IN':
                # IN절의 값들을 분리
                values = [v.strip().strip("'") for v in value.split(',')]
                names.extend(values)
            else:
                names.append(value)
                
        expected_names = ['카뱅', '신한', '우리뱅크', '농협은행', '국민']
        self.assertEqual(sorted(names), sorted(expected_names))

    def test_equal_pattern(self):
        query = "SELECT * FROM table WHERE bank_nm = '카뱅'"
        expected = "SELECT * FROM table WHERE bank_nm = '카카오뱅크'"
        self.assertEqual(self.bank_modifier.modify_query(query), expected)

    def test_multiple_like_patterns(self):
        query = "SELECT * FROM table WHERE bank_nm LIKE '%카뱅%' OR bank_nm LIKE '%농협은행%'"
        expected = "SELECT * FROM table WHERE bank_nm LIKE '%카카오뱅크%' OR bank_nm LIKE '%농협%'"
        self.assertEqual(self.bank_modifier.modify_query(query), expected)

    def test_in_pattern(self):
        query = "SELECT * FROM table WHERE bank_nm IN ('카뱅', '농협은행', '국민')"
        expected = "SELECT * FROM table WHERE bank_nm IN ('카카오뱅크', '농협', 'KB국민은행')"
        self.assertEqual(self.bank_modifier.modify_query(query), expected)

    def test_unknown_nickname(self):
        query = "SELECT * FROM table WHERE bank_nm = '존재하지않는은행'"
        self.assertEqual(self.bank_modifier.modify_query(query), query)

    def test_case_insensitive(self):
        queries = [
            "SELECT * FROM table WHERE BANK_NM = '카뱅'",
            "SELECT * FROM table WHERE bank_NM = '카뱅'",
            "SELECT * FROM table WHERE Bank_Nm = '카뱅'"
        ]
        expected = "SELECT * FROM table WHERE BANK_NM = '카카오뱅크'"
        for query in queries:
            result = self.bank_modifier.modify_query(query)
            self.assertEqual(result.upper(), expected.upper())

if __name__ == '__main__':
    unittest.main()