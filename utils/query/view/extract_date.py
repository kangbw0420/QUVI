import re
from typing import Tuple, Optional
from datetime import datetime, timedelta

from utils.query.view.classify_query import has_subquery

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

def get_date_column(selected_table: str) -> str:
    return 'reg_dt' if selected_table in ['amt', 'stock'] else 'trsc_dt'

def validate_future_date(query: str, date_column: str, flags: dict) -> Tuple[str, Optional[str]]:
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

def extract_view_date(query: str, selected_table: str, flags: dict) -> Tuple[str, str]:
    """뷰테이블에 사용될 날짜 튜플 추출
    Returns:
        Tuple[str, str]: (시작일, 종료일) 형식의 튜플
    Raises:
        ValueError: 날짜 형식이 올바르지 않거나 날짜를 찾을 수 없는 경우
    """
    date_column = get_date_column(selected_table)
    today = datetime.now().strftime("%Y%m%d")
    
    # Check for future dates in BETWEEN clauses first
    between_pattern = f"{date_column}\\s+BETWEEN\\s+'(\\d{{8}})'\\s+AND\\s+'(\\d{{8}})'"
    between_match = re.search(between_pattern, query, re.IGNORECASE)
    
    if between_match:
        start_date = between_match.group(1)
        end_date = between_match.group(2)
        
        # Check if end_date is in the future
        if end_date > today:
            end_date = today
            flags["future_date"] = True
            
        return (start_date, end_date)
    
    # Check subqueries for future dates
    if has_subquery(query):
        # Look for any date pattern in the full query
        date_patterns = [
            r"'(\d{8})'",  # Any date in quotes
            r"BETWEEN\s+'(\d{8})'\s+AND\s+'(\d{8})'"  # BETWEEN pattern
        ]
        
        for pattern in date_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) == 1:
                    date = match.group(1)
                    if date > today:
                        flags["future_date"] = True
                        break
                elif len(match.groups()) == 2:
                    end_date = match.group(2)
                    if end_date > today:
                        flags["future_date"] = True
                        break
    
    # Continue with existing logic for single date validation
    query, modified_date = validate_future_date(query, date_column, flags)
    
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