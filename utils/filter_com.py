import re
from typing import List, Optional

def filter_com(query: str, main_com: str, sub_coms: List[str]) -> str:
    """SQL 쿼리의 회사명(com_nm) 필터 조건을 정제
    
    Args:
        query: 원본 SQL 쿼리
        main_com: 메인 회사명
        sub_coms: 서브 회사명 리스트
    
    Returns:
        str: 회사명 필터가 정제된 SQL 쿼리
        
    처리 규칙:
    1. 단일 회사명이 지정된 경우 그대로 반환
    2. 회사명이 없는 경우 main_com 조건 추가
    3. IN 절에 main_com이 있는 경우 main_com으로 변환
    4. IN 절에 main_com이 없는 경우 첫 번째 회사명으로 변환
    """
    # 회사명 조건 패턴
    single_pattern = r"com_nm\s*=\s*'[^']*'"
    in_pattern = r"com_nm\s+IN\s*\([^)]*\)"
    
    # 모든 회사명 조건 찾기
    com_conditions = []
    com_conditions.extend(re.finditer(single_pattern, query, re.IGNORECASE))
    com_conditions.extend(re.finditer(in_pattern, query, re.IGNORECASE))
    
    if not com_conditions:
        # 회사명 조건이 없는 경우 main_com 조건 추가
        return _add_com_condition(query, main_com)
    
    for match in com_conditions:
        condition = match.group()
        if 'IN' in condition.upper():
            # IN 절 처리
            companies = re.findall(r"'([^']*)'", condition)
            if main_com in companies:
                # main_com이 있으면 main_com으로 변환
                new_condition = f"com_nm = '{main_com}'"
            else:
                # main_com이 없으면 첫 번째 회사명으로 변환
                new_condition = f"com_nm = '{companies[0]}'"
            query = query.replace(condition, new_condition)
    
    return query

def _add_com_condition(query: str, main_com: str) -> str:
    """회사명 조건이 없는 SQL 쿼리에 회사명 조건 추가
    
    Args:
        query: 원본 SQL 쿼리
        main_com: 추가할 회사명
        
    Returns:
        str: 회사명 조건이 추가된 SQL 쿼리
    """
    # WHERE 절 찾기
    where_match = re.search(r'\bWHERE\b', query, re.IGNORECASE)
    
    if where_match:
        # WHERE 절이 있으면 AND 조건으로 추가
        position = where_match.end()
        return (
            f"{query[:position]} com_nm = '{main_com}' AND"
            f"{query[position:]}"
        )
    else:
        # WHERE 절이 없으면 WHERE 절 생성
        # ORDER BY, LIMIT, UNION 등의 위치 찾기
        end_clauses = ['ORDER BY', 'LIMIT', 'UNION']
        positions = []
        
        for clause in end_clauses:
            match = re.search(rf'\b{clause}\b', query, re.IGNORECASE)
            if match:
                positions.append(match.start())
        
        if positions:
            # 가장 앞에 있는 절의 위치에 WHERE 절 삽입
            insert_position = min(positions)
            return (
                f"{query[:insert_position]} WHERE com_nm = '{main_com}' "
                f"{query[insert_position:]}"
            )
        else:
            # 끝에 WHERE 절 추가
            return f"{query} WHERE com_nm = '{main_com}'"