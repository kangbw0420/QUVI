from typing import List, Dict, Any

def is_inout(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """결과 데이터를 입금이면 양수, 출금이면 음수로 분류하고 in_out_dv 컬럼을 제거
    Args:
        result: 입출금이 변환된 데이터
    Returns:
        통화 구분(KRW/FC)으로 그룹화된 결과 데이터
        - KRW 통화 데이터는 desc: 'KRW'로 그룹화
        - 그 외 통화 데이터는 desc: 'FC'로 그룹화
    """
    if not result:
        return result

    # in_out_dv와 trsc_amt가 모두 있는지 확인
    if not any('in_out_dv' in item and 'trsc_amt' in item for item in result):
        return result

    # 각 항목에 대해 변환 수행
    for item in result:
        if 'in_out_dv' in item and 'trsc_amt' in item:
            # 출금인 경우 음수로 변환
            if item['in_out_dv'] == '출금':
                item['trsc_amt'] = -item['trsc_amt']
            # in_out_dv 키 제거
            del item['in_out_dv']

    return result

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