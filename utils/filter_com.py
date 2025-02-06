import re
from typing import List

def normalize_query(query: str) -> str:
    """SQL 쿼리의 포맷을 표준화
    
    - 여러 줄의 공백을 한 줄로
    - 줄 시작과 끝의 공백 제거
    - 괄호 앞뒤 공백 표준화
    """
    # 여러 줄의 공백을 한 줄로
    query = re.sub(r'\s+', ' ', query)
    # 괄호 주위 공백 정리
    query = re.sub(r'\s*\(\s*', ' (', query)
    query = re.sub(r'\s*\)\s*', ') ', query)
    # 쉼표 뒤 공백 추가
    query = re.sub(r',\s*', ', ', query)
    return query.strip()

def filter_com(query: str, main_com: str, sub_coms: List[str], flags: dict) -> str:
    """SQL 쿼리의 회사명(com_nm) 필터 조건을 정제"""
    # UNION 쿼리 처리
    if ' UNION ' in query.upper():
        parts = query.split(' UNION ')
        filtered_parts = [filter_com(part.strip(), main_com, sub_coms) for part in parts]
        return ' UNION '.join(filtered_parts)

    # 쿼리 표준화
    query = normalize_query(query)

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
    
    # 회사명 조건 변환
    result = query
    authorized_companies = [main_com] + sub_coms
    for match in com_conditions:
        condition = match.group()
        if 'IN' in condition.upper():
            # IN 절 처리
            companies = re.findall(r"'([^']*)'", condition)
            if not any(comp in authorized_companies for comp in companies):
                flags["no_access"] = True

            elif main_com in companies:
                new_condition = f"com_nm = '{main_com}'"
            else:
                new_condition = f"com_nm = '{companies[0]}'"
            flags["comp_changed"] = True
            result = result.replace(condition, new_condition)
        else:
            # 단일 회사명 조건 처리
            company = re.findall(r"'([^']*)'", condition)[0]
            if company not in authorized_companies:
                flags["no_access"] = True

    return result

def _add_com_condition(query: str, main_com: str) -> str:
    """회사명 조건이 없는 SQL 쿼리에 회사명 조건 추가"""
    # WHERE 절 찾기
    where_match = re.search(r'\bWHERE\b', query, re.IGNORECASE)
    
    if where_match:
        # WHERE 절이 있으면 AND 조건으로 추가
        position = where_match.end()
        return (
            f"{query[:position]} com_nm = '{main_com}' AND {query[position:].lstrip()}"
        )
    else:
        # WHERE 절이 없으면 WHERE 절 생성
        # ORDER BY, LIMIT 등의 위치 찾기
        end_clauses = ['ORDER BY', 'LIMIT']
        positions = []
        
        for clause in end_clauses:
            match = re.search(rf'\b{clause}\b', query, re.IGNORECASE)
            if match:
                positions.append(match.start())
        
        if positions:
            # 가장 앞에 있는 절의 위치에 WHERE 절 삽입
            insert_position = min(positions)
            return (
                f"{query[:insert_position].rstrip()} WHERE com_nm = '{main_com}' "
                f"{query[insert_position:].lstrip()}"
            )
        else:
            # 끝에 WHERE 절 추가
            return f"{query.rstrip()} WHERE com_nm = '{main_com}'"