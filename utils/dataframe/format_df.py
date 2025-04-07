from typing import Dict, Any, List, Tuple

def delete_useless_col(result: List[Dict[str, Any]], column_list: List[str]) -> List[Dict[str, Any]]:
    """결과 데이터와 컬럼 리스트에서 불필요한 컬럼을 제거합니다.
    
    Args:
        result: SQL 쿼리 실행 결과 데이터
        column_list: 현재 컬럼 리스트
        
    Returns:
        Tuple[List[Dict[str, Any]], List[str]]: 
            - 불필요한 컬럼이 제거된 결과 데이터
            - 갱신된 컬럼 리스트
    """
    # 제거할 컬럼들
    columns_to_delete = {'acct_bal_upd_dtm', 'reg_dtm_upd'}
    
    # 컬럼 리스트에서 제거
    new_column_list = [col for col in column_list if col not in columns_to_delete]
    
    # 결과 형식이 그룹화된 데이터인지 확인
    if isinstance(result, list) and result and isinstance(result[0], dict) and 'data' in result[0]:
        new_result = []
        
        for group in result:
            if 'data' in group and isinstance(group['data'], list):
                # 각 그룹의 데이터에서 컬럼 제거
                new_data = []
                for item in group['data']:
                    new_item = {k: v for k, v in item.items() if k not in columns_to_delete}
                    new_data.append(new_item)
                
                # 새 데이터로 그룹 업데이트
                new_group = group.copy()
                new_group['data'] = new_data
                new_result.append(new_group)
            else:
                # 데이터가 없는 그룹은 그대로 추가
                new_result.append(group)
                
        return new_result
    else:
        # 일반 리스트 형식인 경우 각 항목에서 컬럼 제거
        new_result = [{k: v for k, v in item.items() if k not in columns_to_delete} for item in result]
        return new_result

def final_df_format(result: List[Dict[str, Any]], selected_table: str) -> List[Dict[str, Any]]:
    """선택된 테이블이 trsc인 경우 데이터를 은행명과 계좌번호로 그룹화
    Returns:
        List[Dict[str, Any]]:
        - amt/stock 테이블인 경우: 입력값을 그대로 반환
        - trsc 테이블인 경우: 다음 형식으로 반환
          [
              {
                  'key': {
                      'title': '은행명',
                      'subtitle': '계좌번호'
                  },
                  'data': [{'col1': val1, ...}]  # acct_no, bank_nm 컬럼이 제거된 데이터
              },
              ...
          ]
    """
    # amt 테이블이면 그대로 반환
    if selected_table in ['amt', 'stock', 'api']:
        return [{'data': result}]
        
    # trsc 테이블이 아니면 빈 리스트 반환
    if selected_table != 'trsc':
        return []
        
    # 결과가 비어있는 경우 처리
    if not result:
        return []
        
    # 필요한 컬럼 존재 여부 확인
    required_columns = {'acct_no', 'bank_nm'}
    if not all(col in result[0] for col in required_columns):
        return [{'data': result}]
        
    new_result = []
    bank_accounts = {}
    
    # 데이터를 은행명과 계좌번호로 그룹화
    for row in result:
        bank_nm = row['bank_nm']
        acct_no = row['acct_no']
        # acct_no와 bank_nm을 제외한 새로운 딕셔너리 생성
        data_without_keys = {k: v for k, v in row.items() if k not in ['acct_no', 'bank_nm']}
        
        bank_key = bank_nm
        account_key = f"{bank_nm}_{acct_no}"
        
        if bank_key not in bank_accounts:
            bank_accounts[bank_key] = {}
        if account_key not in bank_accounts[bank_key]:
            bank_accounts[bank_key][account_key] = []
            
        bank_accounts[bank_key][account_key].append(data_without_keys)
    
    # 그룹화된 데이터를 새로운 형식으로 변환
    for bank_nm, accounts in bank_accounts.items():
        for account_key, account_data in accounts.items():
            acct_no = account_key.split('_')[1]  # bank_nm_acct_no에서 acct_no 추출
            new_result.append({
                'key': {
                    'title': bank_nm,
                    'subtitle': acct_no
                },
                'data': account_data
            })
    
    return new_result