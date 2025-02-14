from typing import List, Dict, Any

# 제외할 컬럼 리스트??? ['in_out_dv', 'view_dv', 'com_nm', 'acct_nick_nm', 'acct_dv', 'curr_cd']

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

def delete_upd_dtm(result: List[Dict[str, Any]], column_list: List[str]) -> tuple[List[Dict[str, Any]], List[str]]:
    """결과 데이터와 컬럼 리스트에서 업데이트 시간 관련 정보 제거
    Returns:
        tuple[List[Dict[str, Any]], List[str]]: (업데이트 시간 정보가 제거된 결과, 변환된 컬럼 리스트)
    """
    # 제거할 컬럼들
    columns_to_delete = {'acct_bal_upd_dtm', 'reg_dtm_upd'}
    
    # 컬럼 리스트에서 제거
    new_column_list = [col for col in column_list if col not in columns_to_delete]
    
    # 결과 데이터에서 제거
    new_result = []
    for row in result:
        new_row = {k: v for k, v in row.items() if k not in columns_to_delete}
        new_result.append(new_row)
    
    return new_result, new_column_list

def transform_data(result: List[Dict[str, Any]], column_list: List[str]) -> tuple[List[Dict[str, Any]], List[str]]:
    """
    데이터와 컬럼 리스트를 변환하는 메인 함수
    Returns:
        tuple[List[Dict[str, Any]], List[str]]: (변환된 결과, 변환된 컬럼 리스트)
    """
    # 최종잔액조회일시 컬럼 및 데이터 제거
    result, column_list = delete_upd_dtm(result, column_list)

    # 입출금 변환
    result, column_list = transform_inout_columns(result, column_list)
    
    # 통화 변환
    result, column_list = transform_currency_columns(result, column_list)
    
    return result, column_list