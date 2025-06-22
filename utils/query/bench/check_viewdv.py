import re
from typing import List

def check_view_dv(query: str) -> List[str]:
    """SQL 쿼리에서 view_dv 조건의 값들을 추출합니다.
    
    Args:
        query: SQL 쿼리 문자열
        
    Returns:
        List[str]: view_dv의 값들. 조건이 없으면 빈 리스트 반환
    """
    values = []
    
    # view_dv = '값' 패턴 찾기
    equal_pattern = r"view_dv\s*=\s*'([^']+)'"
    equal_match = re.search(equal_pattern, query, re.IGNORECASE)
    if equal_match:
        values.append(equal_match.group(1))
        return values
        
    # view_dv IN ('값1', '값2', ...) 패턴 찾기
    in_pattern = r"view_dv\s+IN\s*\(\s*([^)]+)\s*\)"
    in_match = re.search(in_pattern, query, re.IGNORECASE)
    if in_match:
        # IN 절 안의 값들을 추출
        in_values = in_match.group(1)
        # 작은따옴표로 둘러싸인 값들을 찾아서 리스트에 추가
        values.extend(re.findall(r"'([^']+)'", in_values))
        
    return values

def is_all_view_dv(values: List[str]) -> bool:
    """view_dv 값들이 모든 계좌 유형을 포함하는지 확인합니다.
    
    Args:
        values: view_dv 값들의 리스트
        
    Returns:
        bool: 모든 계좌 유형('수시', '예적금', '대출', '증권')을 포함하면 True
    """
    required_types = {'수시', '예적금', '대출', '증권'}
    return required_types.issubset(set(values))