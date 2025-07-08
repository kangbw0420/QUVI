from typing import Dict, Any, List

def delete_useless_col(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """결과 데이터와 컬럼 리스트에서 불필요한 컬럼을 제거합니다.
    Args:
        result: SQL 쿼리 실행 결과 데이터
    Returns:
        Tuple[List[Dict[str, Any]], List[str]]: 
            - 불필요한 컬럼이 제거된 결과 데이터
            - 갱신된 컬럼 리스트
    """
    # 제거할 컬럼들
    columns_to_delete = {'acct_bal_upd_dtm', 'reg_dtm_upd'}
    
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