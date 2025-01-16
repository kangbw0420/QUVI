import pandas as pd
from decimal import Decimal
from typing import List, Dict, Any

# 영문 컬럼명에 대한 한글 매핑
COLUMN_MAPPINGS = {
    # 금액(amt) 테이블 관련 컬럼
    'tot_Frequent_acct_amt': '수시입출계좌 인출가능 잔액',
    'tot_saving_acct_amt': '예적금 잔액 합계',
    'tot_loan_acct_amt': '대출 잔액 합계',
    'tot_stock_acct_amt': '증권 잔액 합계',
    'TOT_all_acct_amt': '전체 잔액 합계',
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
    'trsc_month': '거래월'
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
                'tot_Frequent_acct_amt', 'tot_saving_acct_amt', 'tot_loan_acct_amt', 'tot_stock_acct_amt',
                'TOT_all_acct_amt', 'total_acct_bal_amt'],
        'trsc': ['in_cnt', 'curr_amt', 'real_amt', 'loan_rate', 'cnt', 'trsc_cnt', 'trsc_amt', 'trsc_bal', 
                'loan_trsc_amt', 'total_incoming_amount', 'total_outgoing_amount', 'total_incoming', 'total_outgoing']
    }
    
    # 상위 10개 값을 보여줄 컬럼들
    scope_columns = {
        'amt': ['note1', 'avf_load_date', 'note_bal', 'calc_bal'],
        'trsc': ['note1', 'total_trsc_bal', 'trsc_month']
    }
    
    if selected_table in ['amt', 'trsc']:
        # 숫자형 컬럼 처리
        for col in df.columns:
            if col in num_columns[selected_table]:
                korean_col = COLUMN_MAPPINGS.get(col, col)
                try:
                    stats = {
                        "합계": float(df[col].sum()),
                        "평균": float(df[col].mean()),
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