import re
# ORDER BY 조립 위치가 다양해질 수 있어서, 정규식 포기를 고려
from typing import List
from utils.column.extract_column import extract_col_from_query

import sqlglot
from sqlglot.errors import ParseError
from sqlglot.expressions import Subquery

# 포함될 경우 order by의 대상이 되는 컬럼들
DEFAULT_ORDER_COLUMNS = ["reg_dt", "trsc_dt", "trsc_tm"]

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
    # 주석 제거 (-- 스타일과 /* */ 스타일 모두)
    query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
    
    # ORDER BY 검색 (대소문자 구분 없이)    
    pattern = r'\bORDER\s+BY\b'
    return bool(re.search(pattern, query, re.IGNORECASE))

def detect_group_by_aliases(query: str) -> List[str]:
    """GROUP BY 절을 사용한 쿼리에서 별칭을 추출"""
    # GROUP BY 있는지 확인
    group_by_match = re.search(r'\bGROUP\s+BY\b', query, re.IGNORECASE)
    if not group_by_match:
        return []
    
    # SELECT 절에서 AS로 정의된 별칭 찾기
    aliases = []
    select_part = query[:group_by_match.start()]
    alias_pattern = r'(?:.*?\s+AS\s+)(["\w]+)(?:\s*,|$)'
    for match in re.finditer(alias_pattern, select_part, re.IGNORECASE):
        alias = match.group(1).strip('"\'')
        aliases.append(alias)
    
    return aliases


def find_matching_rule(columns: List[str]) -> str:
    """
    추출된 컬럼 조합에 맞는 ORDER BY 규칙 찾기.
    *는 테이블별 기본정렬, 알려지지 않은 컬럼은 DESC 정렬
    """
    columns_set = set(columns)

    # 1. SELECT * 인 경우 테이블별 기본 정렬
    if '*' in columns_set:
        return ""

    # 2. 알려지지 않은 컬럼에 대해 DESC 정렬
    unknown_columns = [col for col in columns if col not in KNOWN_COLUMNS]
    if unknown_columns:
        return ', '.join(f"{col} DESC" for col in unknown_columns)

    # 3. 매칭 안되면 DEFAULT_ORDER_COLUMNS 중 있는 컬럼으로 정렬
    for col in DEFAULT_ORDER_COLUMNS:
        if col in columns_set:
            return f"{col} DESC"
    
    return ""

def has_subquery(query: str) -> bool:
    """
    SQL 쿼리에 서브쿼리가 포함되어 있는지 확인합니다.
    sqlglot 라이브러리를 사용하여 AST를 생성하고, Subquery 노드를 탐색합니다.
    """
    try:
        expression = sqlglot.parse_one(query, dialect='postgres')
        for node in expression.walk():
            if isinstance(node, Subquery):
                return True
        return False
    except ParseError:
        # 파싱 오류 발생 시 안전하게 True 반환 (수정하지 않음)
        return True
    except Exception:
        # 기타 예외 발생 시도 안전하게 True 반환
        return True

def add_order_by(query: str) -> str:
    """SQL 쿼리에 ORDER BY절 추가. 기존 ORDER BY가 있으면 그대로 반환, 없으면 규칙에 따라 ORDER BY 추가
    Returns:
        ORDER BY절이 추가된 SQL 쿼리문 (맨 뒤 세미콜론 포함)
    """
    # 끝의 세미콜론 제거
    query = query.rstrip(';')
    
    # 이미 ORDER BY가 있으면 그대로 반환
    if has_order_by(query):
        return query + ';'
    
    # 서브쿼리가 있으면 그대로 반환
    if has_subquery(query):
        return query + ';'
        
    # 쿼리에서 컬럼 추출
    columns = extract_col_from_query(query)
    if not columns:
        return query
    
    # 별칭(alias) 우선 처리
    aliases = detect_group_by_aliases(query)
    if aliases:
        order_by_clause = f"{aliases[0]} DESC"
    else:
        # ORDER BY 규칙 찾기
        order_by_clause = find_matching_rule(columns)
    
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

    # GROUP BY가 있는 경우 특별 처리
    if "GROUP BY" in query.upper():
        # 쿼리 조립
        result = (
            before_part
            + " ORDER BY "
            + order_by_clause
            + (" " if after_part else "")  # after_part가 있을 때만 공백 추가
            + after_part
        )
    else:
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