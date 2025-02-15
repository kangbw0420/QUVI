import re
from database.postgresql import query_execute

class NameModifier:
    def __init__(self, name_type: str):
        self.name_type = name_type
        self.column_name = f"{name_type}_nm"
        self.table_name = f"{name_type}name"
        self.nick_column = f"{name_type}_nick_nm"
        self.name_mappings = self._load_name_mappings()

    def _load_name_mappings(self) -> dict:
        """Get name mappings from database"""
        query = f"""
            SELECT {self.nick_column}, {self.column_name}
            FROM {self.table_name}
        """
        
        try:
            result = query_execute(query, params=(), use_prompt_db=True)
            return {row[self.nick_column]: row[self.column_name] for row in result}
        except Exception as e:
            print(f"Error loading {self.name_type} mappings: {str(e)}")
            return {}

    def _find_all_patterns(self, query: str) -> list:
        """Find all name patterns in the query"""
        patterns = []
        
        equal_pattern = f"{self.column_name}\\s*=\\s*'([^']*)'+"
        for match in re.finditer(equal_pattern, query, re.IGNORECASE):
            patterns.append((
                match.group(1),
                '=',
                match.group(0)
            ))
            
        in_pattern = f"{self.column_name}\\s+IN\\s*\\(([^)]*)\\)"
        for match in re.finditer(in_pattern, query, re.IGNORECASE):
            patterns.append((
                match.group(1),
                'IN',
                match.group(0)
            ))
                
        # LIKE pattern: column_nm LIKE '%value%'
        like_pattern = f"{self.column_name}\\s+LIKE\\s+'%([^%]+)%'"
        for match in re.finditer(like_pattern, query, re.IGNORECASE):
            patterns.append((
                match.group(1),
                'LIKE',
                match.group(0)
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

stock_modifier = NameModifier('stock')
bank_modifier = NameModifier('bank')

def modify_stock(query: str) -> str:
    return stock_modifier.modify_query(query)

def modify_bank(query: str) -> str:
    return bank_modifier.modify_query(query)