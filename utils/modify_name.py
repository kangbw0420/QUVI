import re
from typing import Optional, Tuple
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

    def _extract_name(self, query: str) -> Tuple[Optional[str], bool]:
        """Extract name value and LIKE operator usage from SQL query
        Args:
            query: SQL query string
        Returns:
            Tuple[Optional[str], bool]: (name value or None, is LIKE pattern)
        """
        # Equal pattern check
        equal_pattern = f"{self.column_name}\s*=\s*'([^']*)'+"
        equal_match = re.search(equal_pattern, query, re.IGNORECASE)
        
        if equal_match:
            return equal_match.group(1), False
            
        # LIKE pattern check
        like_pattern = f"{self.column_name}\s+LIKE\s+'%([^%]+)%'"
        like_match = re.search(like_pattern, query, re.IGNORECASE)
        
        if like_match:
            return like_match.group(1), True
            
        return None, False

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
        # 1. Extract name value from query
        used_name, is_like_pattern = self._extract_name(query)
        if not used_name:
            return query
            
        # 2. & 3. Look up official name
        modified_name = self._get_official_name(used_name)
        if not modified_name:
            return query
            
        # 4. Replace name in query
        if is_like_pattern:
            pattern = f"{self.column_name}\\s+LIKE\\s+'%{used_name}%'"
            replacement = f"{self.column_name} LIKE '%{modified_name}%'"
        else:
            pattern = f"{self.column_name}\\s*=\\s*'{used_name}'"
            replacement = f"{self.column_name} = '{modified_name}'"
        
        modified_query = re.sub(
            pattern,
            replacement,
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