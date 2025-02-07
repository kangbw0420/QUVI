import re
from typing import Optional, Tuple
from database.postgresql import query_execute

def _extract_stock_name(query: str) -> Tuple[Optional[str], bool]:
    """SQL 쿼리에서 stock_nm 값과 LIKE 연산자 사용 여부를 추출
    
    Args:
        query: SQL 쿼리 문자열
        
    Returns:
        Tuple[Optional[str], bool]: (stock_nm 값 또는 None, LIKE 패턴 여부)
    """
    # Equal 패턴 검사 (stock_nm = '삼성전자')
    equal_pattern = r"stock_nm\s*=\s*'([^']*)'+"
    equal_match = re.search(equal_pattern, query, re.IGNORECASE)
    
    if equal_match:
        return equal_match.group(1), False
        
    # LIKE 패턴 검사 (stock_nm LIKE '%삼전%')
    like_pattern = r"stock_nm\s+LIKE\s+'%([^%]+)%'"
    like_match = re.search(like_pattern, query, re.IGNORECASE)
    
    if like_match:
        return like_match.group(1), True
        
    return None, False

def _get_official_stock_name(nickname: str) -> Optional[str]:
    """주식 별칭으로부터 공식 종목명 조회
    Args:
        nickname: 주식 별칭
    Returns:
        Optional[str]: 공식 종목명 또는 매치되지 않으면 None
    """
    query = """
        SELECT stock_nm 
        FROM stockname 
        WHERE stock_nick_nm = %s 
        LIMIT 1
    """
    
    try:
        result = query_execute(query, params=(nickname,), use_prompt_db=True)
        if result and len(result) > 0:
            return str(result[0]['stock_nm'])
    except Exception as e:
        print(f"Error querying stock name: {str(e)}")
    return None

def modify_stock(query: str) -> str:
    """주식 검색 쿼리의 종목명을 공식 종목명으로 변환
    Returns:
        str: 종목명이 변환된 SQL 쿼리
    """
    # 1. 쿼리에서 stock_nm 값 추출
    used_stock_nm, is_like_pattern = _extract_stock_name(query)
    if not used_stock_nm:
        return query
        
    # 2. & 3. stockname 테이블에서 공식 종목명 조회
    modified_stock_nm = _get_official_stock_name(used_stock_nm)
    if not modified_stock_nm:
        return query
        
    # 4. 쿼리 내 종목명 변환
    if is_like_pattern:
        pattern = f"stock_nm\\s+LIKE\\s+'%{used_stock_nm}%'"
        replacement = f"stock_nm LIKE '%{modified_stock_nm}%'"
    else:
        pattern = f"stock_nm\\s*=\\s*'{used_stock_nm}'"
        replacement = f"stock_nm = '{modified_stock_nm}'"
    
    modified_query = re.sub(
        pattern,
        replacement,
        query,
        flags=re.IGNORECASE
    )
    
    return modified_query