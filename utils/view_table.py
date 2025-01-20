from typing import Tuple
import re

def extract_view_date(query: str, selected_table: str) -> Tuple[str, str]:
    """뷰테이블에 사용될 날짜 튜플 추출
    Returns:
        Tuple[str, str]: (시작일, 종료일) 형식의 튜플
            - 단일 날짜가 지정된 경우 해당 날짜를 시작일과 종료일 모두에 사용
            - 날짜 형식은 'YYYYMMDD'
    Raises:
        ValueError: 날짜 형식이 올바르지 않거나 날짜를 찾을 수 없는 경우
    """
    # 테이블 타입에 따른 날짜 컬럼명 결정
    date_column = 'reg_dt' if selected_table == 'amt' else 'trsc_dt'
    
    # BETWEEN 구문이 있는 경우의 패턴
    between_pattern = f"{date_column}\\s+BETWEEN\\s+'(\\d{{8}})'\\s+AND\\s+'(\\d{{8}})'"
    between_match = re.search(between_pattern, query, re.IGNORECASE)
    
    if between_match:
        start_date = between_match.group(1)
        end_date = between_match.group(2)
        return (start_date, end_date)
    
    # 단일 날짜가 있는 경우의 패턴
    single_date_pattern = f"{date_column}\\s*=\\s*'(\\d{{8}})'"
    single_match = re.search(single_date_pattern, query, re.IGNORECASE)
    
    if single_match:
        date = single_match.group(1)
        return (date, date)
    
    raise ValueError(f"날짜를 찾을 수 없습니다. {date_column} 컬럼의 조건을 확인해주세요.")

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
    view_table_part = f"{table_name}({user_id}, {use_intt_id}, {view_date[0]}, {view_date[1]})"
    
    # 최종 쿼리 조립 - FROM 이후의 모든 절을 그대로 유지
    final_query = f"{before_from} FROM {view_table_part} {after_from}"
    
    return final_query