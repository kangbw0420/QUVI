from typing import Tuple, Optional
from datetime import datetime, timedelta
import re

import sqlglot
from sqlglot.errors import ParseError
from sqlglot.expressions import Subquery

def _find_single_date(query: str, date_column: str) -> Optional[Tuple[str, int, int]]:
    """SQL 쿼리에서 단일 날짜 패턴을 찾습니다.
    Returns:
        Optional[Tuple[str, int, int]]: (날짜값, 매치 시작 위치, 매치 끝 위치)
        매치가 없으면 None
    """
    single_date_pattern = f"{date_column}\\s*=\\s*'(\\d{{8}})'"
    match = re.search(single_date_pattern, query, re.IGNORECASE)
    
    if match:
        return (match.group(1), match.start(), match.end())
    return None

def _get_date_column(selected_table: str) -> str:
    return 'reg_dt' if selected_table in ['amt', 'stock'] else 'trsc_dt'

def _validate_future_date(query: str, date_column: str, flags: dict) -> Tuple[str, Optional[str]]:
    """Returns:
        Tuple[str, Optional[str]]: (수정된 쿼리, 수정된 날짜)
        날짜가 수정되지 않았다면 두 번째 요소는 None
    """
    today = datetime.now().strftime("%Y%m%d")
    modified_date = None
    
    # 단일 날짜 패턴 찾기
    single_date_match = _find_single_date(query, date_column)
    
    if single_date_match:
        date_str, start_pos, end_pos = single_date_match
        # 날짜가 오늘보다 미래인 경우
        if date_str > today:
            # 날짜를 오늘 날짜로 변경
            new_condition = f"{date_column} = '{today}'"
            query = query[:start_pos] + new_condition + query[end_pos:]
            modified_date = today
            flags["future_date"] = True
    
    return query, modified_date

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

def extract_view_date(query: str, selected_table: str, flags: dict) -> Tuple[str, str]:
    """뷰테이블에 사용될 날짜 튜플 추출
    Returns:
        Tuple[str, str]: (시작일, 종료일) 형식의 튜플
    Raises:
        ValueError: 날짜 형식이 올바르지 않거나 날짜를 찾을 수 없는 경우
    """
    date_column = _get_date_column(selected_table)
    if has_subquery(query):
        # 서브쿼리 안에서 날짜 조건 찾기
        between_pattern = f"{date_column}\\s+BETWEEN\\s+'(\\d{{8}})'\\s+AND\\s+'(\\d{{8}})'"
        between_match = re.search(between_pattern, query, re.IGNORECASE)
        
        if between_match:
            start_date = between_match.group(1)
            end_date = between_match.group(2)
            
            # 미래 날짜 체크
            today = datetime.now().strftime("%Y%m%d")
            if end_date > today:
                end_date = today
                flags["future_date"] = True
                
            return (start_date, end_date)
    query, modified_date = _validate_future_date(query, date_column, flags)
    
    # due_dt 패턴 확인
    due_dates = None
    due_between_pattern = "due_dt\\s+BETWEEN\\s+'(\\d{8})'\\s+AND\\s+'(\\d{8})'"
    due_between_match = re.search(due_between_pattern, query, re.IGNORECASE)
    
    if due_between_match:
        due_dates = (due_between_match.group(1), due_between_match.group(2))
    else:
        # due_dt의 부등호 패턴
        due_inequality_patterns = [
            (r"due_dt\s*>=\s*'(\d{8})'", r"due_dt\s*<=\s*'(\d{8})'"),
            (r"due_dt\s*>\s*'(\d{8})'", r"due_dt\s*<\s*'(\d{8})'"),
        ]
        
        for start_pattern, end_pattern in due_inequality_patterns:
            start_match = re.search(start_pattern, query, re.IGNORECASE)
            end_match = re.search(end_pattern, query, re.IGNORECASE)
            
            if start_match and end_match:
                due_dates = (start_match.group(1), end_match.group(1))
                break
            elif end_match:
                due_date = end_match.group(1)
                due_dates = (due_date, due_date)
                break
    
    if not due_dates:
        # due_dt 단일 날짜 패턴 확인
        due_single_pattern = r"due_dt\s*=\s*'(\d{8})'"
        due_single_match = re.search(due_single_pattern, query, re.IGNORECASE)
        if due_single_match:
            due_date = due_single_match.group(1)
            due_dates = (due_date, due_date)
    
    # date_column(reg_dt/trsc_dt) 패턴 확인
    between_pattern = f"{date_column}\\s+BETWEEN\\s+'(\\d{{8}})'\\s+AND\\s+'(\\d{{8}})'"
    between_match = re.search(between_pattern, query, re.IGNORECASE)
    
    if between_match:
        start_date = between_match.group(1)
        end_date = between_match.group(2)
        
        # due_dates가 있고 end_date가 due_dates의 끝값보다 큰 경우
        if due_dates and end_date > due_dates[1]:
            return due_dates
        return (start_date, end_date)
    
    # 부등호를 사용한 날짜 범위 패턴
    inequality_patterns = [
        (f"{date_column}\\s*>=\\s*'(\\d{{8}})'", f"{date_column}\\s*<=\\s*'(\\d{{8}})'"),
        (f"{date_column}\\s*>\\s*'(\\d{{8}})'", f"{date_column}\\s*<\\s*'(\\d{{8}})'"),
    ]
    
    for start_pattern, end_pattern in inequality_patterns:
        start_match = re.search(start_pattern, query, re.IGNORECASE)
        end_match = re.search(end_pattern, query, re.IGNORECASE)
        
        if start_match and end_match:
            start_date = start_match.group(1)
            end_date = end_match.group(1)
            
            # due_dates가 있고 end_date가 due_dates의 끝값보다 큰 경우
            if due_dates and end_date > due_dates[1]:
                return due_dates
            return (start_date, end_date)
            
        elif start_match:
            start_date = start_match.group(1)
            end_date = datetime.now().strftime("%Y%m%d")
            
            # due_dates가 있고 현재 날짜가 due_dates의 끝값보다 큰 경우
            if due_dates and end_date > due_dates[1]:
                return due_dates
            return (start_date, end_date)
            
        elif end_match:
            end_date = end_match.group(1)
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
            
            # due_dates가 있고 end_date가 due_dates의 끝값보다 큰 경우
            if due_dates and end_date > due_dates[1]:
                return due_dates
            return (start_date, end_date)
    
    # 단일 날짜가 있는 경우의 패턴
    single_date_match = _find_single_date(query, date_column)
    if single_date_match:
        date = modified_date or single_date_match[0]  # modified_date가 None이면 single_date_match[0] 사용
        # due_dates가 있고 date가 due_dates의 끝값보다 큰 경우
        if due_dates and date > due_dates[1]:
            return due_dates
        return (date, date)
    
    today = datetime.now().strftime("%Y%m%d")
    return (today, today)
    # raise ValueError(f"날짜를 찾을 수 없습니다. {date_column} 또는 due_dt 컬럼의 조건을 확인해주세요.")


def add_view_table(query: str, selected_table: str, view_com: str, user_info: Tuple[str, str], view_date: Tuple[str, str], flags: dict) -> str:
    """SQL 쿼리 테이블 뒤에 뷰테이블 함수를 붙임
    Returns:
        str: 뷰 테이블 구조에 맞게 변환된 SQL 쿼리문
    """
    # 서브쿼리가 있는 경우 처리
    if has_subquery(query):
        user_id, use_intt_id = user_info
        
        # 모든 테이블 참조를 변환
        for table_type in ['amt', 'trsc', 'stock']:
            # 일반 테이블 참조 패턴
            pattern = fr'FROM\s+aicfo_get_all_{table_type}(\s+[a-zA-Z][a-zA-Z0-9_]*)?' 
            view_func = f"aicfo_get_all_{table_type}('{use_intt_id}', '{user_id}', '{view_com}', '{view_date[0]}', '{view_date[1]}')"
            
            def replacement(match):
                alias = match.group(1) or ''  # 별칭이 있으면 사용, 없으면 빈 문자열
                return f"FROM {view_func}{alias}"
                
            # 정규식으로 모든 테이블 참조 교체 (서브쿼리 포함)
            query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
        
        return query
    
    # 이하 기존 로직 (단일 테이블 쿼리 처리)
    date_column = _get_date_column(selected_table)
    query, _ = _validate_future_date(query, date_column, flags)
    
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
    after_from = re.sub(r'^[\w.]+\s*', '', after_from)  # 기존 테이블명 제거
    
    # user_info에서 값을 가져옵니다
    user_id, use_intt_id = user_info
    
    # 뷰 테이블 함수 호출 형식으로 변환
    view_table_part = f"{table_name}('{use_intt_id}', '{user_id}', '{view_com}', '{view_date[0]}', '{view_date[1]}')"
    
    # 최종 쿼리 조립 - FROM 이후의 모든 절을 그대로 유지
    final_query = f"{before_from} FROM {view_table_part} {after_from}"
    
    return final_query