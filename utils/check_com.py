from typing import Union, Sequence, Dict, Any
from sqlalchemy.engine import Result


def check_com_nm(result: Union[Sequence[Dict[str, Any]], Result]) -> Union[Sequence[Dict[str, Any]], Dict[str, Sequence[Dict[str, Any]]]]:
    """
    com_nm 컬럼의 존재 여부와 값의 다양성을 확인하여 결과를 적절히 구조화   
    Returns:
        - com_nm 컬럼이 없는 경우: 원본 결과 그대로 반환
        - com_nm 값이 단일 값인 경우: 원본 결과 그대로 반환
        - com_nm 값이 다수인 경우: com_nm을 키로 하는 딕셔너리로 구조화하여 반환
    """
    # Result 객체인 경우 처리
    if isinstance(result, Result):
        # Result 객체를 딕셔너리 리스트로 변환
        result = [dict(row._mapping) for row in result]
    
    # 빈 결과 처리
    if not result or len(result) == 0:
        return result
        
    # com_nm 컬럼 존재 여부 확인
    first_row = result[0]
    if 'com_nm' not in first_row:
        return result
        
    # com_nm 값들의 집합 생성
    com_nm_set = {row['com_nm'] for row in result}
    
    # 단일 회사인 경우
    if len(com_nm_set) == 1:
        return result
        
    # 다수 회사인 경우: 회사별로 구조화
    structured_result = {}
    for row in result:
        com_nm = row['com_nm']
        if com_nm not in structured_result:
            structured_result[com_nm] = []
        structured_result[com_nm].append(row)
        
    return structured_result