from typing import List, Dict, Any

def extract_col(result: List[Dict[str, Any]]) -> List[str]:
    """
    데이터프레임 형태의 쿼리 결과에서 컬럼명(키)을 추출합니다.
    Returns:
        List[str]: 추출된 컬럼명 리스트
    Examples:
        >>> result = [
        ...     {
        ...         "bank_nm": "우리은행",
        ...         "acct_dv": "수시입출",
        ...         "acct_no": "94300150313001"
        ...     }
        ... ]
        >>> extract_col(result)
        ['bank_nm', 'acct_dv', 'acct_no']
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