from typing import Tuple
import re

from utils.query.view.extract_date import get_date_column, validate_future_date
from utils.query.view.classify_query import has_union, has_subquery

def add_view_table(query: str, selected_table: str, view_com: str, user_info: Tuple[str, str], view_date: Tuple[str, str], flags: dict) -> str:
    """SQL 쿼리의 모든 테이블 참조를 뷰테이블 함수로 변환합니다.
    
    Returns:
        str: 뷰 테이블 구조에 맞게 변환된 SQL 쿼리문
    """
    # UNION이 있는 경우 각 부분을 별도로 처리
    if has_union(query):
        return _process_union_query(query, selected_table, view_com, user_info, view_date, flags)
    
    # UNION이 없는 경우 기존 정규식 기반 방식으로 처리
    return _add_view_table_regex(query, selected_table, view_com, user_info, view_date, flags)

def _process_union_query(query: str, selected_table: str, view_com: str, user_info: Tuple[str, str], view_date: Tuple[str, str], flags: dict) -> str:
    """UNION을 포함하는 쿼리를 처리합니다.
    각 UNION 부분을 개별적으로 처리한 후 다시 결합합니다.
    
    Returns:
        str: 처리된 UNION 쿼리
    """
    # UNION으로 쿼리 분할
    parts = re.split(r'\bUNION\b', query, flags=re.IGNORECASE)
    
    # 각 부분을 개별적으로 처리
    processed_parts = []
    for part in parts:
        processed_part = _add_view_table_regex(part.strip(), selected_table, view_com, user_info, view_date, flags)
        processed_parts.append(processed_part)
    
    # 처리된 부분을 UNION으로 다시 결합
    return " UNION ".join(processed_parts)

def _add_view_table_regex(query: str, selected_table: str, view_com: str, user_info: Tuple[str, str], view_date: Tuple[str, str], flags: dict) -> str:
    """정규식 기반으로 테이블 참조를 뷰테이블 함수로 변환합니다.
    Returns:
        str: 뷰 테이블 구조에 맞게 변환된 SQL 쿼리문
    """
    user_id, use_intt_id = user_info
    date_column = get_date_column(selected_table)
    query, _ = validate_future_date(query, date_column, flags)
    
    # 서브쿼리가 있는 경우 처리
    if has_subquery(query):
        # 1. 메인 FROM 절 처리 (FROM aicfo_get_all_XX)
        main_pattern = r'FROM\s+aicfo_get_all_(\w+)(?:\s+(?:AS\s+)?(\w+))?'
        def replace_main_table(match):
            table_suffix = match.group(1)
            table_alias = match.group(2) or ""
            alias_with_as = f" AS {table_alias}" if table_alias and " AS " in match.group(0) else f" {table_alias}" if table_alias else ""
            table_name = f"aicfo_get_all_{table_suffix}"
            view_table = f"{table_name}('{use_intt_id}', '{user_id}', '{view_com}', '{view_date[0]}', '{view_date[1]}'){alias_with_as}"
            return f"FROM {view_table}"
        
        modified_query = re.sub(main_pattern, replace_main_table, query, flags=re.IGNORECASE)
        
        # 2. JOIN 절 처리 (JOIN aicfo_get_all_XX)
        join_pattern = r'JOIN\s+aicfo_get_all_(\w+)(?:\s+(?:AS\s+)?(\w+))?'
        def replace_join_table(match):
            table_suffix = match.group(1)
            table_alias = match.group(2) or ""
            alias_with_as = f" AS {table_alias}" if table_alias and " AS " in match.group(0) else f" {table_alias}" if table_alias else ""
            table_name = f"aicfo_get_all_{table_suffix}"
            view_table = f"{table_name}('{use_intt_id}', '{user_id}', '{view_com}', '{view_date[0]}', '{view_date[1]}'){alias_with_as}"
            return f"JOIN {view_table}"
        
        final_query = re.sub(join_pattern, replace_join_table, modified_query, flags=re.IGNORECASE)
        
        return final_query
    
    # FROM 절 위치를 찾습니다
    from_pattern = r'FROM\s+'
    match = re.search(from_pattern, query, re.IGNORECASE)
    
    if not match:
        raise ValueError("유효한 FROM 절을 찾을 수 없습니다.")
    
    # 실제 테이블명 조합
    table_name = f"aicfo_get_all_{selected_table}"
    
    # 쿼리를 FROM 위치를 기준으로 나눕니다
    before_from = query[:match.start()].strip()  # SELECT 부분
    after_from = query[match.end():].strip()     # FROM 이후의 모든 부분
    
    # 테이블명 추출 패턴
    table_pattern = r'^(aicfo_get_all_\w+)(?:\s+(?:AS\s+)?(\w+))?'
    table_match = re.search(table_pattern, after_from, re.IGNORECASE)
    
    if table_match:
        existing_table = table_match.group(1)
        alias = table_match.group(2) or ""
        alias_with_as = f" AS {alias}" if alias and "AS" in table_match.group(0) else f" {alias}" if alias else ""
        
        # 기존 테이블명을 제거하고 새 문자열을 구성
        after_from_no_table = after_from[table_match.end():].strip()
        
        # 뷰 테이블 함수 호출 형식으로 변환
        view_table_part = f"{existing_table}('{use_intt_id}', '{user_id}', '{view_com}', '{view_date[0]}', '{view_date[1]}'){alias_with_as}"
        
        # 최종 쿼리 조립
        final_query = f"{before_from} FROM {view_table_part} {after_from_no_table}"
    else:
        # 테이블명이 매치되지 않는 경우, 기본 테이블명으로 가정
        # 뷰 테이블 함수 호출 형식으로 변환
        view_table_part = f"{table_name}('{use_intt_id}', '{user_id}', '{view_com}', '{view_date[0]}', '{view_date[1]}')"
        
        # 최종 쿼리 조립 - FROM 이후의 모든 절을 그대로 유지
        after_from_no_table = re.sub(r'^[\w.]+\s*', '', after_from)  # 기존 테이블명 제거
        final_query = f"{before_from} FROM {view_table_part} {after_from_no_table}"
    
    # JOIN 절에서도 테이블 이름을 뷰 테이블 함수로 대체
    # JOIN aicfo_get_all_XXX table_alias 패턴 찾기
    join_pattern = r'JOIN\s+aicfo_get_all_(\w+)(?:\s+(?:AS\s+)?(\w+))?'
    
    def replace_join_table(match):
        table_suffix = match.group(1)
        table_alias = match.group(2) or ""
        # AS 키워드 유지
        alias_with_as = f" AS {table_alias}" if table_alias and " AS " in match.group(0) else f" {table_alias}" if table_alias else ""
        join_table_name = f"aicfo_get_all_{table_suffix}"
        join_view_table = f"{join_table_name}('{use_intt_id}', '{user_id}', '{view_com}', '{view_date[0]}', '{view_date[1]}'){alias_with_as}"
        return f"JOIN {join_view_table}"
    
    # JOIN 테이블도 치환
    final_query = re.sub(join_pattern, replace_join_table, final_query, flags=re.IGNORECASE)
    
    return final_query