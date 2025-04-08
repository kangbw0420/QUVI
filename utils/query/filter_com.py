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


def extract_table_aliases(query: str) -> list:
    """SQL 쿼리에서 테이블 이름과 별칭을 정확하게 추출

    Returns:
        list: [(테이블명, 별칭)] 형태의 리스트 (별칭이 없으면 테이블명으로 설정)
    """
    tables = []

    # SQL 키워드 목록 (테이블명이나 별칭으로 사용되면 안 되는 단어들)
    sql_keywords = [
        'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER',
        'FULL', 'CROSS', 'ON', 'AND', 'OR', 'NOT', 'GROUP', 'ORDER', 'BY',
        'HAVING', 'LIMIT', 'OFFSET', 'UNION', 'ALL', 'AS', 'DISTINCT', 'BETWEEN'
    ]

    # FROM 절 추출
    from_match = re.search(r'\bFROM\s+(\w+)(?:\s+(?:AS\s+)?(\w+))?', query, re.IGNORECASE)
    if from_match:
        table_name = from_match.group(1)
        alias = from_match.group(2) if from_match.group(2) else table_name

        # SQL 키워드가 아닌지 확인
        if table_name.upper() not in sql_keywords and alias.upper() not in sql_keywords:
            tables.append((table_name, alias))

    # JOIN 절 추출
    join_pattern = re.compile(
        r'\b(?:INNER|LEFT|RIGHT|FULL|CROSS)?\s*JOIN\s+(\w+)(?:\s+(?:AS\s+)?(\w+))?\s+ON\b',
        re.IGNORECASE
    )

    for match in join_pattern.finditer(query):
        table_name = match.group(1)
        alias = match.group(2) if match.group(2) else table_name

        # SQL 키워드가 아닌지 확인
        if table_name.upper() not in sql_keywords and alias.upper() not in sql_keywords:
            tables.append((table_name, alias))

    return tables


def add_com_condition(query: str, company_id: str) -> str:
    """회사명 조건이 없는 SQL 쿼리에 모든 테이블에 대해 회사명 조건 추가

    Args:
        query: SQL 쿼리문
        company_id: 회사 ID
    """
    # UNION 처리 (재귀적으로 각 부분 처리)
    if ' UNION ' in query.upper():
        parts = query.split(' UNION ')
        filtered_parts = [add_com_condition(part.strip(), company_id) for part in parts]
        return ' UNION '.join(filtered_parts)

    # 쿼리 표준화
    query = normalize_query(query)

    # 테이블 정보 추출 (개선된 함수 사용)
    tables = extract_table_aliases(query)

    # 테이블이 추출되지 않았다면 빈 조건 추가 방지
    if not tables:
        # 기본 테이블을 찾을 수 없는 경우, 테이블 별칭 없이 조건 추가
        company_condition = f"com_nm = '{company_id}'"
    else:
        # 모든 테이블에 대한 회사명 조건 생성
        company_conditions = []
        for _, alias in tables:
            company_conditions.append(f"{alias}.com_nm = '{company_id}'")

        company_condition = " AND ".join(company_conditions)

    # WHERE 절 찾기
    where_match = re.search(r'\bWHERE\b', query, re.IGNORECASE)

    if where_match:
        # WHERE 절이 있으면 AND 조건으로 추가
        position = where_match.end()
        return f"{query[:position]} {company_condition} AND {query[position:].lstrip()}"
    else:
        # WHERE 절이 없으면 새로운 WHERE 절 추가
        # ORDER BY, GROUP BY, LIMIT, HAVING 등의 위치 찾기
        end_clauses = ['ORDER BY', 'GROUP BY', 'HAVING', 'LIMIT']
        positions = []

        for clause in end_clauses:
            match = re.search(rf'\b{clause}\b', query, re.IGNORECASE)
            if match:
                positions.append(match.start())

        if positions:
            # 가장 앞에 있는 절의 위치에 WHERE 절 삽입
            insert_position = min(positions)
            return (
                f"{query[:insert_position].rstrip()} WHERE {company_condition} "
                f"{query[insert_position:].lstrip()}"
            )
        else:
            # 끝에 WHERE 절 추가
            return f"{query.rstrip()} WHERE {company_condition}"