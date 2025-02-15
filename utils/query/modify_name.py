import re
from typing import Optional, Tuple, List
from database.postgresql import query_execute

class NameModifier:
    def __init__(self, name_type: str):
        """Initialize with the type of name to modify (e.g., 'stock', 'bank')
        Args:
            name_type: The type of name to modify (determines table and column names)
        """
        self.name_type = name_type
        self.column_name = f"{name_type}_nm"
        self.table_name = f"{name_type}name"
        self.nick_column = f"{name_type}_nick_nm"

    def _extract_names(self, query: str) -> Tuple[List[str], str, bool]:
        """Extract name values and operator type from SQL query
        Args:
            query: SQL query string
        Returns:
            Tuple[List[str], str, bool]: ([name values], operator type, is LIKE pattern)
        """            
        # Equal pattern check
        equal_pattern = f"{self.column_name}\\s*=\\s*'([^']*)'+"
        equal_match = re.search(equal_pattern, query, re.IGNORECASE)
        if equal_match:
            return [equal_match.group(1)], '=', False

        # IN pattern check
        in_pattern = f"{self.column_name}\\s+IN\\s*\\(([^)]*)\\)"
        in_match = re.search(in_pattern, query, re.IGNORECASE)
        if in_match:
            # Extract values from IN clause and clean them
            values_str = in_match.group(1)
            values = [v.strip().strip("'\"") for v in values_str.split(',')]
            return values, 'IN', False
            
        # LIKE pattern check
        like_pattern = f"{self.column_name}\\s+LIKE\\s+'%([^%]+)%'"
        like_match = re.search(like_pattern, query, re.IGNORECASE)
        if like_match:
            return [like_match.group(1)], 'LIKE', True
            
        return [], '', False

    def _get_official_name(self, nickname: str) -> Optional[str]:
        """Look up official name from nickname
        Args:
            nickname: Name alias/nickname
        Returns:
            Optional[str]: Official name or None if no match
        """
        query = f"""
            SELECT {self.column_name}
            FROM {self.table_name}
            WHERE {self.nick_column} = %s
            LIMIT 1
        """
        
        try:
            result = query_execute(query, params=(nickname,), use_prompt_db=True)
            if result and len(result) > 0:
                return str(result[0][self.column_name])
        except Exception as e:
            print(f"Error querying {self.name_type} name: {str(e)}")
        return None

    def modify_query(self, query: str) -> str:
        """Convert names in query to official names
        Args:
            query: Original SQL query
        Returns:
            str: Modified SQL query with official names
        """
        # 1. Extract names and operator type from query
        names, operator, is_like = self._extract_names(query)
        if not names:
            return query
            
        # 2. Look up official names for each name
        official_names = []
        for name in names:
            official_name = self._get_official_name(name)
            if official_name:
                official_names.append(official_name)
            else:
                official_names.append(name)  # Keep original if no match
                
        # 3. Construct replacement based on operator type
        if operator == 'IN':
            quoted_names = [f"'{name}'" for name in official_names]
            names_str = ', '.join(quoted_names)
            new_condition = f"{self.column_name} IN ({names_str})"
            pattern = f"{self.column_name}\\s+IN\\s*\\([^)]*\\)"
        elif operator == 'LIKE':
            new_condition = f"{self.column_name} LIKE '%{official_names[0]}%'"
            pattern = f"{self.column_name}\\s+LIKE\\s+'%{names[0]}%'"
        else:  # Equal operator
            new_condition = f"{self.column_name} = '{official_names[0]}'"
            pattern = f"{self.column_name}\\s*=\\s*'{names[0]}'"
        
        # 4. Replace in query
        modified_query = re.sub(
            pattern,
            new_condition,
            query,
            flags=re.IGNORECASE
        )
        
        return modified_query

# Create instances for specific name types
stock_modifier = NameModifier('stock')
bank_modifier = NameModifier('bank')

def modify_stock(query: str) -> str:
    """Legacy wrapper for stock name modification"""
    return stock_modifier.modify_query(query)

def modify_bank(query: str) -> str:
    """Wrapper for bank name modification"""
    return bank_modifier.modify_query(query)