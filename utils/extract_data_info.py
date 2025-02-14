import re
from typing import List, Dict, Any

def extract_col_from_query(query: str) -> List[str]:
    """SELECT절에서 컬럼명 추출. alias가 있으면 alias를, 테이블명 접두사가 있으면 제거하고 컬럼명만 반환"""
    # SELECT와 FROM 사이의 내용 추출
    select_pattern = re.compile(r'SELECT\s+(.*?)\s+FROM', re.IGNORECASE | re.DOTALL)
    match = select_pattern.search(query)
    if not match:
        return []
    
    columns_str = match.group(1).strip()
    
    # SELECT * 처리
    if columns_str == '*':
        return ['*']
        
    # 컬럼들을 분리하고 정리
    columns = []
    # alias가 있을 경우 alias를 컬럼명으로 사용
    column_pattern = re.compile(r'(?:.*?\s+AS\s+)?(["\w]+)(?:\s*,|$)', re.IGNORECASE)
    
    # 인식된 컬럼명을 정제
    for match in column_pattern.finditer(columns_str):
        col = match.group(1)
        # 테이블 접두사 제거
        col = col.split('.')[-1]
        # 공백과 따옴표 제거
        col = col.strip().strip('"\'')
        if col:
            columns.append(col)
            
    return columns

def extract_col_from_dict(result: List[Dict[str, Any]]) -> List[str]:
    """
    데이터프레임 형태의 쿼리 결과에서 컬럼명(키)을 추출합니다.
    Returns:
        List[str]: 추출된 컬럼명 리스트
    Raises:
        ValueError: result가 비어있거나 유효하지 않은 형식인 경우
    """
    # 입력 검증
    if not result:
        raise ValueError("Result list is empty")
        
    if not isinstance(result, list):
        raise ValueError("Result must be a list")
        
    if not isinstance(result[0], dict):
        raise ValueError("Result items must be dictionaries")
        
    # 첫 번째 레코드에서 키(컬럼명)를 추출
    # 모든 레코드는 동일한 구조를 가지므로 첫 번째 레코드만 확인
    columns = list(result[0].keys())
    
    if not columns:
        raise ValueError("No columns found in result")
        
    return columns