from typing import Tuple
from datetime import datetime, timedelta
import re

def extract_view_date(query: str, selected_table: str) -> Tuple[str, str]:
    """뷰테이블에 사용될 날짜 튜플 추출
    Returns:
        Tuple[str, str]: (시작일, 종료일) 형식의 튜플
    Raises:
        ValueError: 날짜 형식이 올바르지 않거나 날짜를 찾을 수 없는 경우
    """
    # 테이블 타입에 따른 날짜 컬럼명 결정
    date_column = 'reg_dt' if selected_table in ['amt', 'stock'] else 'trsc_dt'
    
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
    single_date_pattern = f"{date_column}\\s*=\\s*'(\\d{{8}})'"
    single_match = re.search(single_date_pattern, query, re.IGNORECASE)
    
    if single_match:
        date = single_match.group(1)
        # due_dates가 있고 date가 due_dates의 끝값보다 큰 경우
        if due_dates and date > due_dates[1]:
            return due_dates
        return (date, date)
    
    raise ValueError(f"날짜를 찾을 수 없습니다. {date_column} 또는 due_dt 컬럼의 조건을 확인해주세요.")

def add_view_table(query: str, selected_table: str, user_info: Tuple[str, str], view_date: Tuple[str, str]) -> str:
    """SQL 쿼리 테이블 뒤에 뷰테이블 함수를 붙임
    Returns:
        str: 뷰 테이블 구조에 맞게 변환된 SQL 쿼리문
            예: "SELECT * FROM aicfo_get_all_amt('user123', 'intt456', '20250101', '20250131') 
                WHERE view_dv = '대출' AND reg_dt = '20250120'"
    """
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
    view_table_part = f"{table_name}('{use_intt_id}', '{user_id}', '{view_date[0]}', '{view_date[1]}')"
    
    # 최종 쿼리 조립 - FROM 이후의 모든 절을 그대로 유지
    final_query = f"{before_from} FROM {view_table_part} {after_from}"
    
    return final_query
