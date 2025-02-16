import re

def check_view_dv(query: str) -> str:
    """SQL 쿼리에서 view_dv 조건의 값을 추출합니다.
    
    Args:
        query: SQL 쿼리 문자열
        
    Returns:
        str: view_dv의 값. 조건이 없으면 빈 문자열 반환
    """
    # view_dv = '값' 패턴 찾기
    pattern = r"view_dv\s*=\s*'([^']+)'"
    match = re.search(pattern, query, re.IGNORECASE)
    
    if match:
        return match.group(1)  # 작은따옴표 안의 값을 반환
    return ""