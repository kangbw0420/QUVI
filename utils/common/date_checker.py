from datetime import datetime
from typing import Tuple, Optional

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
            
        # 각 월의 일수 체크 (윤년 고려)
        days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        # 윤년 체크 (4로 나누어 떨어지고 100으로 나누어 떨어지지 않거나, 400으로 나누어 떨어지는 해)
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            days_in_month[2] = 29
            
        if day > days_in_month[month]:
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
    
    # 두 날짜가 모두 유효한 경우
    if from_date_valid and to_date_valid:
        return None

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