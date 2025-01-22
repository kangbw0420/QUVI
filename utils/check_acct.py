from typing import Dict, Any, List

def check_acct_no(result: List[Dict[str, Any]], selected_table: str) -> List[Dict[str, Any]]:
    """
    선택된 테이블이 trsc인 경우 회사별로 묶인 데이터를 계좌번호별로 추가 그룹화
    
    Args:
        result: check_com_nm의 결과
        selected_table: 선택된 테이블 ('amt' 또는 'trsc')
        
    Returns:
        List[Dict[str, Any]]:
        - amt 테이블인 경우: 입력값을 그대로 반환
        - trsc 테이블인 경우: 다음 형식으로 반환
          [
              {
                  'key': {
                      'title': '회사명',
                      'subtitle': '계좌번호'
                  },
                  'data': [{'col1': val1, ...}]  # acct_no 컬럼이 제거된 데이터
              },
              ...
          ]
    """
    # amt 테이블이면 그대로 반환
    if selected_table == 'amt':
        return result
        
    # trsc 테이블이 아니면 빈 리스트 반환
    if selected_table != 'trsc':
        return []
        
    # 결과가 비어있는 경우 처리
    if not result:
        return []
        
    new_result = []
    
    # 각 회사별 데이터 처리
    for company_group in result:
        company_name = company_group['key']['title']
        company_data = company_group['data']
        
        # 첫 번째 데이터로 acct_no 컬럼 존재 여부 확인
        if not company_data or 'acct_no' not in company_data[0]:
            continue
            
        # 회사 내 데이터를 계좌번호별로 그룹화
        accounts = {}
        for row in company_data:
            acct_no = row['acct_no']
            # acct_no를 제외한 새로운 딕셔너리 생성
            data_without_acct = {k: v for k, v in row.items() if k != 'acct_no'}
            
            if acct_no not in accounts:
                accounts[acct_no] = []
            accounts[acct_no].append(data_without_acct)
        
        # 계좌번호별로 그룹화된 데이터를 새로운 형식으로 변환
        for acct_no, acct_data in accounts.items():
            new_result.append({
                'key': {
                    'title': company_name,
                    'subtitle': acct_no
                },
                'data': acct_data
            })
    
    return new_result