from typing import Dict, Any, List

def check_acct_no(result: List[Dict[str, Any]], selected_table: str) -> List[Dict[str, Any]]:
    """
    선택된 테이블이 trsc인 경우 데이터를 은행명과 계좌번호로 그룹화
    
    Args:
        result: SQL 쿼리 실행 결과 리스트
        selected_table: 선택된 테이블 ('amt' 또는 'trsc')
        
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
    if selected_table in ['amt', 'stock']:
        return result
        
    # trsc 테이블이 아니면 빈 리스트 반환
    if selected_table != 'trsc':
        return []
        
    # 결과가 비어있는 경우 처리
    if not result:
        return []
        
    # 필요한 컬럼 존재 여부 확인
    required_columns = {'acct_no', 'bank_nm'}
    if not all(col in result[0] for col in required_columns):
        return result
        
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