from datetime import datetime
from typing import Tuple, Optional

def is_leap_year(year: int) -> bool:
    """윤년인지 확인합니다.
    Returns:
        bool: 윤년이면 True, 아니면 False
    """
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

def get_days_in_month(year: int, month: int) -> int:
    """해당 연도, 월의 마지막 일수를 반환합니다.
    Returns:
        int: 해당 월의 일수
    """
    days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    # 윤년이면 2월을 29일로 조정
    if month == 2 and is_leap_year(year):
        return 29
    
    return days_in_month[month]

def is_valid_date(date_str: str) -> bool:
    """날짜 문자열(YYYYMMDD 형식)이 유효한 날짜인지 확인합니다.
    Returns:
        bool: 유효한 날짜인 경우 True, 그렇지 않은 경우 False
    """
    if not date_str or len(date_str) != 8:
        return False
        
    try:
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        
        # 기본적인 범위 체크
        if not (1 <= month <= 12) or not (1 <= day <= 31):
            return False
            
        # 해당 월의 마지막 일자 체크
        days_in_month = get_days_in_month(year, month)
        if day > days_in_month:
            return False
            
        # datetime 객체로 변환 가능한지 최종 확인
        datetime.strptime(date_str, '%Y%m%d')
        return True
        
    except ValueError:
        return False

def format_date_for_message(date_str: str) -> str:
    """날짜 문자열(YYYYMMDD)을 'YY년 MM월 DD일' 형식으로 변환"""
    if not date_str or len(date_str) != 8:
        return date_str
        
    try:
        year = date_str[:4]
        month = date_str[4:6].lstrip('0')  # 앞의 0 제거 (예: '01' -> '1')
        day = date_str[6:8].lstrip('0')    # 앞의 0 제거 (예: '01' -> '1')
        
        return f"{year}년 {month}월 {day}일"
    except:
        return date_str

def correct_date(date_str: str) -> str:
    """유효하지 않은 날짜를 가장 가까운 유효한 날짜로 교정합니다.
    예: '20240230'(2월 30일) -> '20240229'(윤년의 2월 29일) 또는 '20230228'(평년의 2월 28일)
    
    Returns:
        str: 교정된 날짜(YYYYMMDD 형식)
    """
    if is_valid_date(date_str):
        return date_str
        
    if not date_str or len(date_str) != 8:
        return date_str
        
    try:
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        
        # 월이 유효한 범위(1-12)인지 확인
        if not (1 <= month <= 12):
            # 유효하지 않은 월은 가장 가까운 유효한 월로 교정
            month = max(1, min(month, 12))
        
        # 해당 월의 마지막 일자 가져오기
        max_day = get_days_in_month(year, month)
        
        # 일이 유효한 범위(1-해당 월의 마지막 일)인지 확인
        if not (1 <= day <= max_day):
            # 유효하지 않은 일은 가장 가까운 유효한 일로 교정
            day = max(1, min(day, max_day))
        
        # 교정된 날짜 반환
        return f"{year:04d}{month:02d}{day:02d}"
        
    except:
        return date_str

def correct_date_range(date_info: Tuple[str, str]) -> Tuple[str, str]:
    """날짜 범위에서 시작일과 종료일을 모두 교정합니다.
    
    Returns:
        Tuple[str, str]: 교정된 (시작일, 종료일) 튜플
    """
    if not date_info or len(date_info) != 2:
        return date_info
        
    from_date, to_date = date_info
    
    # 두 날짜 모두 교정
    corrected_from = correct_date(from_date)
    corrected_to = correct_date(to_date)
    
    return (corrected_from, corrected_to)

def check_date(date_info: Tuple[str, str], flags: dict) -> Optional[str]:
    """date_info 튜플의 날짜들이 유효한지 검사하고, 유효하지 않은 경우 적절한 오류 메시지를 반환합니다.
    Returns:
        Optional[str]: 날짜가 유효하지 않은 경우 오류 메시지, 모두 유효한 경우 None
    """
    if not date_info or len(date_info) != 2:
        return None

    from_date, to_date = date_info

    from_date_valid = is_valid_date(from_date)
    to_date_valid = is_valid_date(to_date)

    # 유효하지 않은 날짜가 있는 경우 메시지 생성
    if not from_date_valid or not to_date_valid:
        flags["invalid_date"] = True
        # 두 날짜가 모두 유효하지 않고 같은 경우
        if from_date == to_date:
            formatted_date = format_date_for_message(from_date)
            return f"해당 요청을 처리하기 위해 {formatted_date}의 데이터를 조회하려고 했으나, {formatted_date}은(는) 유효하지 않은 날짜입니다. 명확하게 날짜를 말씀주셔서 제가 제대로 판단할 수 있게 도와주시면 감사하겠습니다!"
        # 두 날짜가 모두 유효하지 않고 다른 경우
        else:
            formatted_from = format_date_for_message(from_date)
            formatted_to = format_date_for_message(to_date)
            return f"해당 요청을 처리하기 위해 {formatted_from}부터 {formatted_to}까지의 데이터를 조회하려고 했으나, 두 날짜 모두 유효하지 않은 날짜입니다. 명확하게 날짜를 말씀주셔서 제가 제대로 판단할 수 있게 도와주시면 감사하겠습니다!"
    
    return None