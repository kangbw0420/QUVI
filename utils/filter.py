import json
from typing import Union, List, Dict, Any

def columns_filter(query_result: Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]], 
                  selected_table_name: str) -> Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """쿼리 결과에서 테이블과 view_dv에 따라 필요한 컬럼만 필터링
    
    Args:
        query_result: 쿼리 실행 결과 (리스트 또는 회사별로 구조화된 딕셔너리)
        selected_table_name: 선택된 테이블명 ('amt' 또는 'trsc')
    
    Returns:
        필터링된 결과 (입력과 동일한 구조)
    """
    if not query_result:
        return query_result

    with open("temp.json", "r", encoding="utf-8") as f:
        columns_list = json.load(f)

    if selected_table_name not in ["amt", "trsc"]:
        return query_result

    def filter_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not data:
            return data
            
        view_dv = data[0].get("view_dv", "전체")
        columns_to_remove = columns_list[selected_table_name][view_dv]
        
        return [{k: v for k, v in row.items() if k not in columns_to_remove}
                for row in data]

    # 회사별로 구조화된 딕셔너리인 경우
    if isinstance(query_result, dict):
        return {
            company: filter_data(company_data)
            for company, company_data in query_result.items()
        }
    
    # 단일 리스트인 경우
    return filter_data(query_result)