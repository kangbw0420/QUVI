import re
from typing import List

# 컬럼에 따른 ORDER BY 규칙 정의
COLUMN_ORDER_RULES = {
    ('note1',): 'note1 DESC',
    ('note1', 'note2'): 'note1 DESC, note2 DESC',
    ('trsc_dt', 'trsc_tm'): 'trsc_dt DESC, trsc_tm DESC',
    ('bank_nm',): 'bank_nm DESC',
    # ... 추가 규칙들
}

DEFAULT_ORDER_RULES = {
    "amt": "com_nm DESC, curr_cd DESC, reg_dt DESC, acct_bal_amt DESC",
    "trsc": "com_nm DESC, curr_cd DESC, trsc_dt DESC, trsc_tm DESC, seq_no DESC"
}

# 알려진 모든 컬럼들의 집합
KNOWN_COLUMNS = {col for rule in COLUMN_ORDER_RULES.keys() for col in rule}

def has_order_by(query: str) -> bool:
    """쿼리에 ORDER BY절이 있는지 확인"""
    # 주석 제거 (-- 스타일과 /* */ 스타일 모두)
    query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
    
    # ORDER BY 검색 (대소문자 구분 없이)
    pattern = r'\bORDER\s+BY\b'
    return bool(re.search(pattern, query, re.IGNORECASE))

def extract_columns(query: str) -> List[str]:
    """SELECT 절에서 컬럼들을 추출"""
    # SELECT와 FROM 사이의 내용 추출
    select_pattern = re.compile(r'SELECT\s+(.*?)\s+FROM', re.IGNORECASE | re.DOTALL)
    match = select_pattern.search(query)
    if not match:
        return []
    
    columns_str = match.group(1).strip()
    
    # SELECT * 처리
    if columns_str == '*':
        return ['*']
        
    # 컬럼들을 분리하고 정리
    columns = []
    for col in columns_str.split(','):
        # 별칭(AS) 처리
        col = col.split(' AS ')[0].split(' as ')[0]
        # 테이블명 제거 (table.column -> column)
        col = col.split('.')[-1]
        # 공백과 따옴표 제거
        col = col.strip().strip('"\'')
        if col:
            columns.append(col)
            
    return columns

def find_matching_rule(columns: List[str], selected_table: str) -> str:
    """추출된 컬럼에 맞는 ORDER BY 규칙 찾기"""
    columns_set = set(columns)
    
    # SELECT * 인 경우 테이블별 기본 정렬
    if '*' in columns_set:
        return DEFAULT_ORDER_RULES.get(selected_table, DEFAULT_ORDER_RULES["trsc"])
    
    # 알려지지 않은 컬럼들 찾기
    unknown_columns = [col for col in columns if col not in KNOWN_COLUMNS]
    if unknown_columns:
        # 알려지지 않은 컬럼들을 순서대로 DESC 정렬
        return ', '.join(f"{col} DESC" for col in unknown_columns)
        
    # 컬럼 조합에 맞는 규칙 찾기
    for rule_columns, order_by in COLUMN_ORDER_RULES.items():
        if all(col in columns_set for col in rule_columns):
            return order_by
            
    # 매칭되는 규칙이 없으면 테이블별 기본값 반환
    return DEFAULT_ORDER_RULES.get(selected_table, DEFAULT_ORDER_RULES["trsc"])

def add_order_by(query: str, selected_table: str) -> str:
    """SQL 쿼리에 ORDER BY 절 추가"""
    # 이미 ORDER BY가 있으면 그대로 반환
    if has_order_by(query):
        return query
        
    # 쿼리에서 컬럼 추출
    columns = extract_columns(query)
    if not columns:
        return query
        
    # ORDER BY 규칙 찾기
    order_by_clause = find_matching_rule(columns, selected_table)
    
    # LIMIT, UNION 위치 찾기 (대소문자 구분 없이)
    query_upper = query.upper()
    limit_pos = query_upper.find("LIMIT ")
    union_pos = query_upper.find("UNION ")

    # ORDER BY를 삽입할 위치 결정
    if limit_pos != -1 and union_pos != -1:
        # LIMIT와 UNION이 모두 있는 경우 앞쪽에 있는 것 기준
        insert_pos = min(limit_pos, union_pos)
    elif limit_pos != -1:
        # LIMIT만 있는 경우
        insert_pos = limit_pos
    elif union_pos != -1:
        # UNION만 있는 경우
        insert_pos = union_pos
    else:
        # 아무 것도 없는 경우
        insert_pos = len(query)

    # 쿼리 조립
    result = (
        query[:insert_pos].rstrip()
        + " ORDER BY "
        + order_by_clause
        + " "
        + query[insert_pos:].lstrip()
    )

    # 마지막에 세미콜론 추가
    return result + ";"