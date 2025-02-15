import re
from typing import List
from utils.extract_data_info import extract_col_from_query

# 컬럼에 따른 ORDER BY 규칙 정의
COLUMN_ORDER_RULES = {
    ('bank_nm', 'acct_dv', 'acct_no', 'acct_bal_amt',
     'real_amt', 'acct_bal_upd_dtm'
     ): 'acct_bal_amt DESC',
    ('bank_nm', 'acct_no', 'acct_bal_amt', 'real_amt',
     'curr_cd', 'acct_dv', 'acct_nick_nm', 'acct_bal_upd_dtm'
     ): 'curr_cd DESC, acct_bal_amt DESC',
    ('bank_nm', 'acct_no', 'trsc_dt', 'trsc_tm', 'note1',
     'in_out_dv', 'trsc_amt', 'trsc_bal'
     ): 'trsc_dt DESC, trsc_tm DESC',
    ('bank_nm', 'acct_no', 'trsc_dt', 'trsc_tm',  'curr_cd',
     'note1', 'in_out_dv', 'trsc_amt','trsc_bal'
     ): 'curr_cd DESC, trsc_dt DESC, trsc_tm DESC'
}

DEFAULT_ORDER_RULES = {
    "amt": "reg_dt DESC",
    "trsc": "trsc_dt DESC",
    "stock": "reg_dt DESC"
}

# 알려진 모든 컬럼들의 집합
KNOWN_COLUMNS = {
    "amt": [
        "view_dv", "bank_nm", "acct_no", "curr_cd", "reg_dt", 
        "acct_bal_amt", "acct_bal_won", "acct_nick_nm", "open_dt", "due_dt", 
        "trmn_yn", "trmn_dt", "acct_bal_upd_dtm", "real_amt", "cntrct_amt", 
        "intr_rate", "acct_dv", "mnth_pay_amt", "mnth_pay_dt", "stock_nm", 
        "bal_qunt", "prchs_price", "prchs_amt", "tot_prchs_amt", "curr_amt", 
        "valu_gain_loss", "appr_amt", "tot_appr_amt", "purchase_amt_foreign", 
        "evaluation_amt_foreign", "return_rate", "deposit_foreign", "tot_asset_amt", 
        "deposit_amt"
    ],
    "trsc": [
        "view_dv", "bank_nm", "acct_no", "curr_cd", "seq_no", 
        "reg_dt", "trsc_tm", "in_out_dv", "trsc_amt", "trsc_bal", "note1", 
        "acct_dv", "acct_nick_nm", "loan_trsc_amt", "loan_rate", "stock_nm", 
        "item_qunt", "fee_amt", "pres_qunt", "pres_amt"
    ], 
    "stock": [
        "bank_nm", "acct_no", "curr_cd", "reg_dt", "acct_dv", 
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