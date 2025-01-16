import pandas as pd
from decimal import Decimal
from typing import List, Dict, Any

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
    
    if selected_table == 'amt':
        target_columns = ['cntrct_amt', 'curr_amt', 'valu_gain_loss', 'return_rate', 'tot_asset_amt', 'deposit_amt', 'tot_Frequent_acct_amt', 'tot_saving_acct_amt', 'tot_loan_acct_amt', 'tot_stock_acct_amt', 'TOT_all_acct_amt', 'total_acct_bal_amt', 'in_cnt']
        existing_columns = [col for col in target_columns if col in df.columns]
        
        for col in existing_columns:
            stats = {
                "합계": float(df[col].sum()),
                "평균": float(df[col].mean()),
                "개수": int(df[col].count())
            }
            result_parts.append(
                f"{col}에 대한 통계:\n"
                f"- 합계: {stats['합계']:,.2f}\n"
                f"- 평균: {stats['평균']:,.2f}\n"
                f"- 데이터 수: {stats['개수']:,}개"
            )
            
    elif selected_table == 'trsc':
        target_columns = ['curr_amt', 'real_amt', 'loan_rate', 'cnt', 'trsc_cnt', 'tot_trsc_bal', 'total_incoming_amount', 'total_outgoing_amount']
        existing_columns = [col for col in target_columns if col in df.columns]
        
        for col in existing_columns:
            stats = {
                "합계": float(df[col].sum()),
                "평균": float(df[col].mean()),
                "개수": int(df[col].count())
            }
            result_parts.append(
                f"{col}에 대한 통계:\n"
                f"- 합계: {stats['합계']:,.2f}\n"
                f"- 평균: {stats['평균']:,.2f}\n"
                f"- 데이터 수: {stats['개수']:,}개"
            )
    
    return result_parts