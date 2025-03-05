import re

def normalize_query(query: str) -> str:
    """SQL 쿼리의 포맷을 표준화"""
    # 여러 줄의 공백을 한 줄로
    query = re.sub(r'\s+', ' ', query)
    # 괄호 주위 공백 정리
    query = re.sub(r'\s*\(\s*', ' (', query)
    query = re.sub(r'\s*\)\s*', ') ', query)
    # 쉼표 뒤 공백 추가
    query = re.sub(r',\s*', ', ', query)
    return query.strip()
    
def add_com_condition(query: str, company_id: str) -> str:
    """회사명 조건이 없는 SQL 쿼리에 회사명 조건 추가"""
    # WHERE 절 찾기
    
    if ' UNION ' in query.upper():
        parts = query.split(' UNION ')
        filtered_parts = [add_com_condition(part.strip(), company_id) for part in parts]
        return ' UNION '.join(filtered_parts)

    # 쿼리 표준화
    query = normalize_query(query)
    
    where_match = re.search(r'\bWHERE\b', query, re.IGNORECASE)
    
    if where_match:
        # WHERE 절이 있으면 AND 조건으로 추가
        position = where_match.end()
        return (
            f"{query[:position]} com_nm = '{company_id}' AND {query[position:].lstrip()}"
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
                f"{query[:insert_position].rstrip()} WHERE com_nm = '{company_id}' "
                f"{query[insert_position:].lstrip()}"
            )
        else:
            # 끝에 WHERE 절 추가
            return f"{query.rstrip()} WHERE com_nm = '{company_id}'"