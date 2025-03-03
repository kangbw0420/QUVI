from typing import List, Dict, Any

def is_null_only(result):
    """
    결과 데이터가 있지만 모든 값이 None/null인지 확인합니다.
    """
    if not result:
        return True
        
    # 결과가 리스트이고 각 항목이 딕셔너리인 경우
    if isinstance(result, list) and all(isinstance(item, dict) for item in result):
        for item in result:
            # 하나라도 null이 아닌 값이 있으면 False 반환
            if any(value is not None for value in item.values()):
                return False
        # 모든 값이 null이면 True 반환
        return True
    
    return False

def is_krw(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """결과 데이터를 curr_cd를 기준으로 KRW와 FC 그룹으로 분류

    Args:
        result: API 결과 데이터

    Returns:
        통화 구분(KRW/FC)으로 그룹화된 결과 데이터
        - KRW 통화 데이터는 desc: 'KRW'로 그룹화
        - 그 외 통화 데이터는 desc: 'FC'로 그룹화
    """
    if not result or 'data' not in result[0]:
        return result

    # 통화별로 데이터 분류
    krw_data = []
    fc_data = []
    
    for item in result[0]['data']:
        if item['curr_cd'] == 'KRW':
            krw_data.append(item)
        else:
            fc_data.append(item)

    # 새로운 형식으로 결과 구성
    new_result = []
    
    # KRW 데이터가 있으면 추가
    if krw_data:
        new_result.append({
            'key': {'desc': '원화자금'},
            'data': krw_data
        })
    
    # FC 데이터가 있으면 추가
    if fc_data:
        new_result.append({
            'key': {'desc': '외화자금'},
            'data': fc_data
        })

    return new_result