import sqlparse
from typing import List, Dict, Any
import re

def extract_col_from_query(query: str) -> List[str]:
    """SELECT절에서 컬럼명을 추출하며 복잡한 표현식과 별칭을 올바르게 처리
    Returns:
        List[str]: 추출된 컬럼명 리스트 (별칭이 있으면 별칭 사용)
    """
    try:
        parsed = sqlparse.parse(query)[0]
    except (IndexError, TypeError):
        return []
    
    if not parsed.get_type() == 'SELECT':
        return []
    
    columns = []
    
    select_stmt = None
    for token in parsed.tokens:
        if token.ttype is None and isinstance(token, sqlparse.sql.IdentifierList):
            select_stmt = token
            break
        elif token.ttype is None and isinstance(token, sqlparse.sql.Parenthesis):
            continue
        elif token.is_keyword and token.value.upper() == 'FROM':
            break
    
    if not select_stmt:
        # SELECT * FROM pattern check
        for token in parsed.tokens:
            if token.value == '*':
                return ['*']
        
        # alternative: use regex
        return extract_columns_with_regex(query)
    
    # extract column from IdentifierList
    for token in select_stmt.tokens:
        if token.ttype is sqlparse.tokens.Punctuation:  # 쉼표 건너뛰기
            continue
            
        column_name = extract_column_name(token)
        if column_name:
            columns.append(column_name)
            
    return columns

def extract_column_name(token):
    """토큰에서 컬럼명 또는 별칭 추출"""
    if token.ttype is not None and token.ttype not in sqlparse.tokens.Literal:
        # 맨 처음 토큰이 기본 유형이면 건너뛰기
        return None
        
    # 별칭이 있는 경우
    if hasattr(token, 'get_alias') and token.get_alias():
        alias = token.get_alias()
        # 따옴표 제거
        return alias.strip('"\'`[]')
        
    # Identifier 유형인 경우
    if isinstance(token, sqlparse.sql.Identifier):
        # 테이블 접두사 제거하고 반환
        name = token.get_real_name() or token.value
        return name.strip('"\'`[]')
        
    # 함수인 경우
    if isinstance(token, sqlparse.sql.Function):
        func_name = token.get_name()
        if func_name:
            return func_name
            
    # 기타 경우: 전체 값 반환
    if token.value and token.value.strip():
        return token.value.strip()
        
    return None

def extract_columns_with_regex(query: str) -> List[str]:
    """정규식을 사용하여 SELECT 절에서 컬럼을 추출"""
    # 주석 제거
    query = re.sub(r'--.*?(\n|$)', ' ', query)
    query = re.sub(r'/\*.*?\*/', ' ', query, flags=re.DOTALL)
    
    # SELECT와 FROM 사이 부분 추출
    match = re.search(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE | re.DOTALL)
    if not match:
        return []
        
    select_clause = match.group(1).strip()
    
    # SELECT * 처리
    if select_clause == '*':
        return ['*']
        
    # 컬럼 표현식 분리
    columns = []
    column_expressions = split_column_expressions(select_clause)
    
    for expr in column_expressions:
        expr = expr.strip()
        
        # 별칭 추출 (AS 키워드가 있는 경우)
        alias_match = re.search(r'\bAS\s+(["\[])?([\w\s]+)(["\]])?(?:\s*$|\s*,)', expr, re.IGNORECASE)
        if alias_match:
            columns.append(alias_match.group(2).strip())
            continue
            
        # 별칭 추출 (AS 키워드 없이 공백으로 구분된 경우)
        alias_match = re.search(r'(?:^|[^"\w])([\w\.]+)\s+(["\[])?([\w\s]+)(["\]])?(?:\s*$|\s*,)', expr)
        if alias_match:
            columns.append(alias_match.group(3).strip())
            continue
            
        # 함수 이름 추출
        func_match = re.match(r'([a-zA-Z0-9_]+)\s*\(', expr)
        if func_match:
            columns.append(func_match.group(1))
            continue
            
        # 단순 컬럼명 처리
        simple_col = expr.split('.')[-1].strip('"\'`[] ')
        if simple_col:
            columns.append(simple_col)
            
    return columns

def split_column_expressions(select_text: str) -> List[str]:
    """SELECT 절의 컬럼 표현식을 올바르게 분리합니다.
    중첩된 함수와 괄호를 고려합니다.
    Returns:
        List[str]: 분리된 컬럼 표현식 리스트
    """
    expressions = []
    current_expr = ""
    paren_count = 0
    quote_char = None
    
    for char in select_text:
        # 따옴표 처리 (문자열 내부에서는 괄호와 쉼표를 무시)
        if char in "\"'`" and (quote_char is None or char == quote_char):
            if quote_char is None:
                quote_char = char
            else:
                quote_char = None
        
        # 괄호 카운팅
        if quote_char is None:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
        
        # 컬럼 분리 (최상위 레벨에서의 쉼표)
        if char == ',' and paren_count == 0 and quote_char is None:
            expressions.append(current_expr.strip())
            current_expr = ""
        else:
            current_expr += char
    
    # 마지막 표현식 추가
    if current_expr:
        expressions.append(current_expr.strip())
    
    return expressions

def extract_col_from_dict(result: List[Dict[str, Any]]) -> List[str]:
    """데이터프레임 형태의 쿼리 결과에서 컬럼명(키)을 추출합니다.
    Returns:
        List[str]: 추출된 컬럼명 리스트        
    Raises:
        ValueError: result가 비어있거나 유효하지 않은 형식인 경우
    """
    # 입력 검증
    if not result:
        raise ValueError("Result list is empty")
        
    if not isinstance(result, list):
        raise ValueError("Result must be a list")
        
    if not isinstance(result[0], dict):
        raise ValueError("Result items must be dictionaries")
        
    # 첫 번째 레코드에서 키(컬럼명)를 추출
    # 모든 레코드는 동일한 구조를 가지므로 첫 번째 레코드만 확인
    columns = list(result[0].keys())
    
    if not columns:
        raise ValueError("No columns found in result")
        
    return columns