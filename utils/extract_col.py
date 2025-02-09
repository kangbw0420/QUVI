from typing import List, Dict, Any

def extract_col(result: List[Dict[str, Any]]) -> List[str]:
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

def transform_inout_columns(result: List[Dict[str, Any]], column_list: List[str]) -> tuple[List[Dict[str, Any]], List[str]]:
    """
    입출금(in_out_dv) 관련 컬럼을 변환하는 함수
    
    Args:
        result: SQL 쿼리 실행 결과
        column_list: 원본 컬럼 리스트
    
    Returns:
        tuple[List[Dict[str, Any]], List[str]]: (변환된 결과, 변환된 컬럼 리스트)
    """
    if not result or 'in_out_dv' not in column_list or 'trsc_amt' not in column_list:
        return result, column_list
    
    # 새로운 결과와 컬럼 리스트 생성
    new_result = []
    new_column_list = column_list.copy()
    
    # in_out_dv와 trsc_amt 컬럼의 인덱스 찾기
    inout_idx = new_column_list.index('in_out_dv')
    amt_idx = new_column_list.index('trsc_amt')
    
    # 컬럼 리스트 수정
    new_column_list.remove('in_out_dv')
    new_column_list.remove('trsc_amt')
    new_column_list.extend(['trsc_deposit', 'trsc_withdrawal'])
    
    # 각 레코드 변환
    for row in result:
        new_row = row.copy()
        inout_type = new_row.pop('in_out_dv')
        amount = new_row.pop('trsc_amt')
        
        if inout_type == '입금':
            new_row['trsc_deposit'] = amount
            new_row['trsc_withdrawal'] = None
        else:  # '출금'
            new_row['trsc_deposit'] = None
            new_row['trsc_withdrawal'] = amount
            
        new_result.append(new_row)
    
    return new_result, new_column_list

def transform_currency_columns(result: List[Dict[str, Any]], column_list: List[str]) -> tuple[List[Dict[str, Any]], List[str]]:
    """
    통화(curr_cd) 관련 컬럼을 변환하는 함수
    
    Args:
        result: SQL 쿼리 실행 결과
        column_list: 원본 컬럼 리스트
    
    Returns:
        tuple[List[Dict[str, Any]], List[str]]: (변환된 결과, 변환된 컬럼 리스트)
    """
    if not result or 'curr_cd' not in column_list:
        return result, column_list
        
    # 통화 종류 수집
    currencies = {row['curr_cd'] for row in result}
    
    # 새로운 컬럼 리스트 생성
    new_column_list = []
    base_columns = [col for col in column_list if col != 'curr_cd']
    
    # 통화별로 컬럼 추가
    for curr in sorted(currencies):
        for col in base_columns:
            new_column_list.append(f"{curr}_{col}")
    
    # 새로운 결과 생성
    new_result = []
    for row in result:
        new_row = {}
        curr = row['curr_cd']
        for col in base_columns:
            new_row[f"{curr}_{col}"] = row[col]
        new_result.append(new_row)
    
    return new_result, new_column_list

def transform_data(result: List[Dict[str, Any]], column_list: List[str]) -> tuple[List[Dict[str, Any]], List[str]]:
    """
    데이터와 컬럼 리스트를 변환하는 메인 함수
    Returns:
        tuple[List[Dict[str, Any]], List[str]]: (변환된 결과, 변환된 컬럼 리스트)
    """
    # 입출금 변환
    result, column_list = transform_inout_columns(result, column_list)
    
    # 통화 변환
    result, column_list = transform_currency_columns(result, column_list)
    
    return result, column_list