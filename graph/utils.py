import json
import pandas as pd
from decimal import Decimal
from typing import List, Dict

# 영문 컬럼명에 대한 한글 매핑
COLUMN_MAPPINGS = {
    # 금액(amt) 테이블 관련 컬럼
    'tot_frequent_acct_amt': '수시입출계좌 인출가능 잔액',
    'tot_saving_acct_amt': '예적금 잔액 합계',
    'tot_loan_acct_amt': '대출 잔액 합계',
    'tot_stock_acct_amt': '증권 잔액 합계',
    'tot_all_acct_amt': '전체 잔액 합계',
    'total_acct_bal_amt': '총 합계 잔액',
    'acct_bal_amt': '잔고',
    'intr_rate': '이자율',
    'real_amt': '인출가능잔액',
    'cntrct_amt': '약정금액',
    'return_rate': '수익률',
    'tot_asset_amt': '총자산',
    'deposit_amt': '예수금',
    'note1': '적요',
    'avf_load_date': '평균 대출 금리',
    'note_bal': '항목 잔액',
    'calc_bal': '항목 비중',
    'net_balance': '순수익',
    'avg_intr_rate': '평균대출금리',
    'avg_interest_rate': '평균대출금리',
    'total_research_fee': '연구비',
    'total_research_amount': '연구비',
    'research_exepense_ratio': '연구비 비중',
    'percentage_research_expense': '연구비 비중',
    'percentage_research_expenses': '연구비 비중',
    'research_expense_amount': '연구비금액',
    'total_research_expense': '연구비',
    'total_withdrawal_amount': '출금액 합계',

    'note1': '적요',
    'bank_nm': '은행명',

    # 거래(trsc) 테이블 관련 컬럼
    'in_cnt': '입금 건수',
    'cnt': '거래 건수',
    'trsc_cnt': '거래 건수',
    'total_incoming_amount': '입금총액',
    'total_incoming': '입금총액',
    'total_outgoing_amount': '출금총액',
    'total_outgoing': '출금총액',
    'trsc_amt': '거래금액',
    'trsc_bal': '잔액',
    'loan_rate': '이율',
    'loan_trsc_amt': '거래원금',
    'total_trsc_bal': '순수익',
    'trsc_month': '거래월',
    'tot_profit': '순이익'
}

def analyze_data(data: List[Dict], selected_table: str) -> str:
    """데이터프레임의 각 컬럼 타입을 자동으로 감지하여 분석합니다.
    Args:
        data: 분석할 데이터
        selected_table: 테이블 유형 ('amt' 또는 'trsc')
    Returns:
        str: 분석 결과를 담은 문자열
    """
    # DataFrame 생성
    df = pd.DataFrame(data)
    print("$" * 80)
    print(df.columns)
    
    if len(df) == 0:
        return "데이터가 없습니다."
        
    result_parts = []
    
    # Decimal 타입을 float로 변환
    for col in df.columns:
        if isinstance(df[col].iloc[0] if len(df) > 0 else None, Decimal):
            df[col] = df[col].astype(float)
    
    # 통계를 계산할 숫자형 컬럼들
    num_columns = {
        'amt': ['cntrct_amt', 'real_amt', 'acct_bal_amt', 'return_rate', 'tot_asset_amt', 'deposit_amt', 
                'tot_frequent_acct_amt', 'tot_saving_acct_amt', 'tot_loan_acct_amt', 'tot_stock_acct_amt',
                'tot_all_acct_amt', 'total_acct_bal_amt', 'avg_interest_rate',
                'avg_intr_rate'],
        'trsc': ['in_cnt', 'curr_amt', 'real_amt', 'loan_rate', 'cnt', 'trsc_cnt', 'trsc_amt', 'trsc_bal', 'net_balance', 
                'loan_trsc_amt', 'total_incoming_amount', 'total_outgoing_amount', 'total_incoming', 'total_outgoing',
                'percentage_research_expense', 'percentage_research_expenses', 'research_expense_amount',
                'tot_profit']
    }
    
    # 상위 10개 값을 보여줄 컬럼들
    scope_columns = {
        'amt': ['note1', 'avf_load_date', 'note_bal', 'calc_bal', 'bank_nm'],
        'trsc': ['note1', 'total_trsc_bal', 'trsc_month', 'bank_nm']
    }
    
    if selected_table in ['amt', 'trsc']:
        # 숫자형 컬럼 처리
        for col in df.columns:
            if col in num_columns[selected_table]:
                korean_col = COLUMN_MAPPINGS.get(col, col)
                try:
                    stats = {
                        "합계": int(df[col].sum()),
                        "평균": int(df[col].mean()),
                        "개수": int(df[col].count())
                    }
                    result_str = (
                        f"{korean_col}에 대한 통계:\n"
                        f"- 합계: {stats['합계']:,.2f}\n"
                        f"- 평균: {stats['평균']:,.2f}\n"
                        f"- 데이터 수: {stats['개수']:,}개"
                    )
                    result_parts.append(result_str)
                except (TypeError, ValueError) as e:
                    print(f"Warning: Could not calculate statistics for column {col}: {str(e)}")
            
            # scope 컬럼 처리
            elif col in scope_columns[selected_table] and len(df) > 0:
                korean_col = COLUMN_MAPPINGS.get(col, col)
                values = df[col].head(10).tolist()
                # 숫자인 경우에만 포맷팅
                try:
                    formatted_values = [f"{float(v):,.2f}" if isinstance(v, (int, float, Decimal)) else str(v) 
                                     for v in values]
                except (TypeError, ValueError):
                    formatted_values = [str(v) for v in values]
                
                result_str = f"{korean_col}의 주요 값 리스트: {formatted_values}"
                result_parts.append(result_str)
    
    return result_parts

def add_order_by(query: str, selected_table: str) -> str:
    """SQL 쿼리에 ORDER BY 절을 추가하는 함수
    Returns:
        str: ORDER BY 절이 추가된 SQL 쿼리
    """
    if not query:
        return query

    # SELECT * 쿼리인지 확인 (8번째 문자가 '*'인지 체크)
    if len(query) <= 8 or query[7] != '*':
        return query

    # 이미 ORDER BY가 있는지 확인
    if "ORDER BY" in query.upper():
        return query

    # 우선 세미콜론 제거
    query = query.strip(';')

    # 테이블별 기본 정렬 기준 설정
    default_order = {
        'amt': 'ORDER BY com_nm DESC, curr_cd DESC, reg_dt DESC, acct_bal_amt DESC',  # 계좌구분 오름차순
        'trsc': 'ORDER BY com_nm DESC, curr_cd DESC, trsc_dt DESC, trsc_tm DESC, seq_no DESC'  # 거래일시 내림차순
    }

    order_clause = default_order.get(selected_table, '')
    
    # LIMIT, UNION 위치 찾기 (대소문자 구분 없이)
    query_upper = query.upper()
    limit_pos = query_upper.find("LIMIT ")
    union_pos = query_upper.find("UNION ")
    
    # ORDER BY를 삽입할 위치 결정
    if limit_pos != -1 and union_pos != -1:
        # LIMIT와 UNION이 모두 있는 경우 앞쪽에 있는 것 기준
        insert_pos = min(limit_pos, union_pos)
    elif limit_pos != -1:
        # LIMIT만 있는 경우
        insert_pos = limit_pos
    elif union_pos != -1:
        # UNION만 있는 경우
        insert_pos = union_pos
    else:
        # 아무 것도 없는 경우
        insert_pos = len(query)
    
    # 쿼리 조립
    result = query[:insert_pos].rstrip() + " " + order_clause + " " + query[insert_pos:].lstrip()
    
    # 마지막에 세미콜론 추가
    return result + ";"
    
def columns_filter(query_result: list, selected_table_name:str):
    result = query_result

    with open("temp.json", 'r', encoding='utf-8') as f: # 테이블에 따른 컬럼리스트
        columns_list = json.load(f)
        
    # node에서 query_result 의 element 존재유무를 검사했으니 column name 기준으로 '거래내역'과 '잔액'을 구분
    if selected_table_name == "trsc":
        filtered_result = []    # 필터링한 결과를 출력할 변수
        # view_dv로 인텐트트 구분
        if 'view_dv' in result[0]:
            columns_to_remove = columns_list['trsc'][result[0]['view_dv']]
            for x in result:
                x = {k: v for k, v in x.items() if k not in columns_to_remove}
                filtered_result.append(x)
        else:   # view_dv가 없기 때문에 '전체'에 해당되는 column list만 출력
            columns_to_remove = columns_list['trsc']['전체']
            for x in result:
                x = {k: v for k, v in x.items() if k not in columns_to_remove}
                filtered_result.append(x)
        return filtered_result
    elif selected_table_name == "amt":
        filtered_result = []
        if 'view_dv' in result[0]:
            columns_to_remove = columns_list['amt'][result[0]['view_dv']]
            for x in result:
                x = {k: v for k, v in x.items() if k not in columns_to_remove}
                filtered_result.append(x)
        else:
            columns_to_remove = columns_list['amt']['전체']
            for x in result:
                x = {k: v for k, v in x.items() if k not in columns_to_remove}
                filtered_result.append(x)
        return filtered_result
    else:  # 해당사항 없으므로 본래 resul값 출력 
        return result