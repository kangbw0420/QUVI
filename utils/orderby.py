import re
from typing import List

# 컬럼에 따른 ORDER BY 규칙 정의
COLUMN_ORDER_RULES = {
    ('com_nm', 'bank_nm', 'acct_dv', 'acct_no', 'acct_bal_amt',
     'real_amt', 'acct_bal_upd_dtm'
     ): 'com_nm DESC, acct_bal_amt DESC',
    ('com_nm', 'bank_nm', 'acct_no', 'acct_bal_amt', 'real_amt',
     'curr_cd', 'acct_dv', 'acct_nick_nm', 'acct_bal_upd_dtm'
     ): 'com_nm DESC, curr_cd DESC, acct_bal_amt DESC',
    ('com_nm', 'bank_nm', 'acct_no', 'trsc_dt', 'trsc_tm', 'note1',
     'in_out_dv', 'trsc_amt', 'trsc_bal'
     ): 'com_nm DESC, trsc_dt DESC, trsc_tm DESC',
    ('com_nm', 'bank_nm', 'acct_no', 'trsc_dt', 'trsc_tm',  'curr_cd',
     'note1', 'in_out_dv', 'trsc_amt','trsc_bal'
     ): 'com_nm DESC, curr_cd DESC, trsc_dt DESC, trsc_tm DESC'
}

DEFAULT_ORDER_RULES = {
    "amt": "com_nm DESC, reg_dt DESC",
    "trsc": "com_nm DESC, trsc_dt DESC",
    "stock": "com_nm DESC, reg_dt DESC"
}

# 알려진 모든 컬럼들의 집합
KNOWN_COLUMNS = {
    "amt": [
        "view_dv", "com_nm", "bank_nm", "acct_no", "curr_cd", "reg_dt", 
        "acct_bal_amt", "acct_bal_won", "acct_nick_nm", "open_dt", "due_dt", 
        "trmn_yn", "trmn_dt", "acct_bal_upd_dtm", "real_amt", "cntrct_amt", 
        "intr_rate", "acct_dv", "mnth_pay_amt", "mnth_pay_dt", "stock_nm", 
        "bal_qunt", "prchs_price", "prchs_amt", "tot_prchs_amt", "curr_amt", 
        "valu_gain_loss", "appr_amt", "tot_appr_amt", "purchase_amt_foreign", 
        "evaluation_amt_foreign", "return_rate", "deposit_foreign", "tot_asset_amt", 
        "deposit_amt"
    ],
    "trsc": [
        "view_dv", "com_nm", "bank_nm", "acct_no", "curr_cd", "seq_no", 
        "reg_dt", "trsc_tm", "in_out_dv", "trsc_amt", "trsc_bal", "note1", 
        "acct_dv", "acct_nick_nm", "loan_trsc_amt", "loan_rate", "stock_nm", 
        "item_qunt", "fee_amt", "pres_qunt", "pres_amt"
    ], 
    "stock": [
        "com_nm", "bank_nm", "acct_no", "curr_cd", "reg_dt", "acct_dv", 
        "stock_nm", "bal_qunt", "prchs_price", "prchs_amt", "curr_amt", 
        "valu_gain_loss", "appr_amt", "purchase_amt_foreign", 
        "evaluation_amt_foreign", "return_rate"
    ]
}

def has_order_by(query: str) -> bool:
    """SQL 쿼리에 ORDER BY절 존재 여부 확인. 주석은 제거하고 검사"""
    # 주석 제거 (-- 스타일과 /* */ 스타일 모두)
    query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
    
    # ORDER BY 검색 (대소문자 구분 없이)    
    pattern = r'\bORDER\s+BY\b'
    return bool(re.search(pattern, query, re.IGNORECASE))

def extract_col_from_query(query: str) -> List[str]:
    """SELECT절에서 컬럼명 추출. alias가 있으면 alias를, 테이블명 접두사가 있으면 제거하고 컬럼명만 반환"""
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
    # alias가 있을 경우 alias를 컬럼명으로 사용
    column_pattern = re.compile(r'(?:.*?\s+AS\s+)?(["\w]+)(?:\s*,|$)', re.IGNORECASE)
    
    # 인식된 컬럼명을 정제
    for match in column_pattern.finditer(columns_str):
        col = match.group(1)
        # 테이블 접두사 제거
        col = col.split('.')[-1]
        # 공백과 따옴표 제거
        col = col.strip().strip('"\'')
        if col:
            columns.append(col)
            
    return columns

def find_matching_rule(columns: List[str], selected_table: str) -> str:
    """추출된 컬럼 조합에 맞는 ORDER BY 규칙 찾기. *는 테이블별 기본정렬, 알려지지 않은 컬럼은 DESC 정렬"""
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
    """SQL 쿼리에 ORDER BY절 추가. 기존 ORDER BY가 있으면 그대로 반환, 없으면 규칙에 따라 ORDER BY 추가
    Returns:
        ORDER BY절이 추가된 SQL 쿼리문 (맨 뒤 세미콜론 포함)
    """
    # 이미 ORDER BY가 있으면 그대로 반환
    if has_order_by(query):
        return query
        
    # 쿼리에서 컬럼 추출
    columns = extract_col_from_query(query)
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

    before_part = query[:insert_pos].rstrip(';').rstrip()
    after_part = query[insert_pos:].lstrip().rstrip(';')

    # 쿼리 조립
    result = (
        before_part
        + " ORDER BY "
        + order_by_clause
        + (" " if after_part else "")  # after_part가 있을 때만 공백 추가
        + after_part
    )

    # 마지막에 세미콜론 추가
    return result + ";"