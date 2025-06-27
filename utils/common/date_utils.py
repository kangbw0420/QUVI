from datetime import datetime, timedelta

def get_today() -> datetime:
    """현재 날짜와 시간을 반환"""
    return datetime.now()

def get_today_str() -> str:
    """현재 날짜를 YYYYMMDD 형식의 문자열로 반환"""
    return get_today().strftime("%Y%m%d")

def get_today_formatted() -> str:
    """현재 날짜를 'YYYY년 MM월 DD일' 형식의 문자열로 반환"""
    return get_today().strftime("%Y년 %m월 %d일")

def get_today_dash() -> str:
    """현재 날짜를 'YYYY-MM-DD' 형식의 문자열로 반환"""
    return get_today().strftime("%Y-%m-%d")

def get_weekday() -> str:
    """현재 요일을 한글 문자열로 반환"""
    WEEKDAYS = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}
    return WEEKDAYS[get_today().weekday()]

def format_date_with_weekday() -> str:
    """현재 날짜와 요일을 'YYYYMMDD 요일요일' 형식으로 반환"""
    return f"{get_today_str()} {get_weekday()}요일"

def convert_date_format(date_str: str) -> str:
    """다양한 날짜 형식을 YYYYMMDD 형식으로 변환
    Args:
        date_str: 변환할 날짜 문자열 (YYYYMMDD 또는 YYYY-MM-DD 형식)
    Returns:
        YYYYMMDD 형식의 날짜 문자열
    """
    # 공백 제거
    date_str = date_str.strip()

    if len(date_str) == 8 and date_str.isdigit():
        return date_str
    # YYYY-MM-DD 형식 검사 및 변환
    elif len(date_str) == 10 and date_str[4] == "-" and date_str[7] == "-":
        return date_str.replace("-", "")
    return date_str

def add_days(date_str: str, days: int) -> str:
    """날짜 문자열에 일수를 더하거나 뺌
    Args:
        date_str: YYYYMMDD 형식의 날짜 문자열
        days: 더하거나 뺄 일수 (음수면 빼기)
    Returns:
        YYYYMMDD 형식의 날짜 문자열
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y%m%d")
        new_date = date_obj + timedelta(days=days)
        return new_date.strftime("%Y%m%d")
    except Exception as e:
        print(f"Error adding days to date: {e}")
        return date_str

def is_future_date(date_str: str) -> bool:
    """날짜가 미래인지 확인
    Args:
        date_str: YYYYMMDD 형식의 날짜 문자열
    Returns:
        미래 날짜면 True, 아니면 False
    """
    try:
        return date_str > get_today_str()
    except:
        return False

def check_past_date_access(from_date: str, days_threshold: int = 2) -> bool:
    """과거 데이터 접근 제한 체크
    Args:
        from_date: YYYYMMDD 형식의 시작 날짜
        days_threshold: 과거 데이터 접근 제한 일수 (기본값: 2일)
    Returns:
        제한된 과거 데이터면 True, 아니면 False
    """
    try:
        from_dt = datetime.strptime(from_date, "%Y%m%d")
        date_diff = get_today() - from_dt
        return date_diff.days >= days_threshold
    except:
        return False 