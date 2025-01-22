from typing import Union, Sequence, Dict, Any, List
from sqlalchemy.engine import Result

def check_com_nm(result: Union[Sequence[Dict[str, Any]], Result]) -> List[Dict[str, Any]]:
    """
    데이터를 회사별로 그룹화하여 새로운 형식으로 반환
    
    Args:
        result: SQL 쿼리 실행 결과 (Result 객체 또는 딕셔너리 시퀀스)
        
    Returns:
        List[Dict[str, Any]]: 다음 형식의 리스트
        [
            {
                'key': {
                    'title': '회사명',  # 회사명이 없으면 빈 문자열('')
                    'subtitle': '계좌번호'  # subtitle은 선택적(nullable)
                },
                'data': [{'col1': val1, ...}]  # com_nm 컬럼이 제거된 데이터
            },
            ...
        ]
    """
    # Result 객체인 경우 딕셔너리 리스트로 변환
    if isinstance(result, Result):
        result = [dict(row._mapping) for row in result]
    
    # 빈 결과 처리
    if not result or len(result) == 0:
        return []
        
    # com_nm 컬럼 존재 여부 확인
    first_row = result[0]
    has_company = 'com_nm' in first_row
    
    if not has_company:
        # com_nm 컬럼이 없는 경우 빈 문자열을 title로 사용
        return [{
            'key': {
                'title': ''  # subtitle은 생략 (nullable)
            },
            'data': result
        }]
    
    # 회사별로 데이터 그룹화
    companies = {}
    for row in result:
        com_nm = row['com_nm']
        # com_nm을 제외한 새로운 딕셔너리 생성
        data_without_com = {k: v for k, v in row.items() if k != 'com_nm'}
        
        if com_nm not in companies:
            companies[com_nm] = []
        companies[com_nm].append(data_without_com)
    
    # 요구사항에 맞는 새로운 형식으로 변환
    structured_result = [
        {
            'key': {
                'title': com_nm if com_nm else ''  # 빈 문자열 대체
            },
            'data': company_data
        }
        for com_nm, company_data in companies.items()
    ]
    
    return structured_result