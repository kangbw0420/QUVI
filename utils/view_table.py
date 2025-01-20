from typing import Tuple
import re

def extract_view_date(query: str) -> Tuple[str, str]:
    """
    SQL 쿼리에서 조회 시작일과 종료일을 추출합니다.
    
    Args:
        query (str): 분석할 SQL 쿼리문
            예: "SELECT * FROM aicfo_get_all_amt WHERE reg_dt = '20250120'"
            또는 "SELECT * FROM aicfo_get_all_amt WHERE reg_dt BETWEEN '20250101' AND '20250131'"
    
    Returns:
        Tuple[str, str]: (시작일, 종료일) 형식의 튜플
            - 단일 날짜가 지정된 경우 해당 날짜를 시작일과 종료일 모두에 사용
            - 날짜 형식은 'YYYYMMDD'
    
    Examples:
        >>> query = "SELECT * FROM table WHERE reg_dt = '20250120'"
        >>> extract_view_date(query)
        ('20250120', '20250120')
    """
    pass

def add_view_table(query: str, user_info: Tuple[str, str], view_date: Tuple[str, str]) -> str:
    """
    SQL 쿼리를 뷰 테이블 구조에 맞게 변환합니다.
    Args:
        query (str): 변환할 원본 SQL 쿼리문
        user_info (Tuple[str, str]): (user_id, use_intt_id) 형식의 사용자 정보
        view_date (Tuple[str, str]): (시작일, 종료일) 형식의 조회 기간
    Returns:
        str: 뷰 테이블 구조에 맞게 변환된 SQL 쿼리문
    """
    # FROM 절과 테이블명만 찾습니다
    from_pattern = r'FROM\s+(\w+)'
    match = re.search(from_pattern, query, re.IGNORECASE)
    
    if not match:
        raise ValueError("유효한 FROM 절을 찾을 수 없습니다.")
    
    table_name = match.group(1)
    
    # 쿼리를 FROM 위치를 기준으로 나눕니다
    before_from = query[:match.start()].strip()  # SELECT 부분
    after_from = query[match.end():].strip()     # FROM 이후의 모든 부분
    
    # user_info에서 값을 가져옵니다
    user_id, use_intt_id = user_info
    
    # 뷰 테이블 함수 호출 형식으로 변환
    view_table_part = f"{table_name}('{user_id}', '{use_intt_id}', '{view_date[0]}', '{view_date[1]}')"
    
    # 최종 쿼리 조립 - FROM 이후의 모든 절을 그대로 유지
    final_query = f"{before_from} FROM {view_table_part} {after_from}"
    
    return final_query