from typing import Dict, List, Any, Union
import pandas as pd
from string import Formatter

from utils.logger import setup_logger
from utils.table.safe_eval import SafeExpressionEvaluator

logger = setup_logger('calc_table')

def evaluate_fstring(fstring: str, data: Union[List[Dict[str, Any]], pd.DataFrame]) -> str:
    """
    f-string 형식의 템플릿 문자열을 평가하여 결과 문자열을 반환합니다.
    
    Args:
        fstring: f-string 형식의 템플릿 문자열 (예: "이름: {df['name']}")
        data: 표현식 평가에 사용할 데이터
        
    Returns:
        평가된 결과 문자열
    """
    try:
        # f-string 마커 제거 (f"..." 또는 f'...')
        if fstring.startswith('f"') and fstring.endswith('"'):
            fstring = fstring[2:-1]
        elif fstring.startswith("f'") and fstring.endswith("'"):
            fstring = fstring[2:-1]
        
        evaluator = SafeExpressionEvaluator(data)
        formatter = Formatter()
        result_parts = []
        
        for literal_text, field_name, format_spec, conversion in formatter.parse(fstring):
            # 리터럴 텍스트 추가
            result_parts.append(literal_text)
            
            # 표현식 필드가 없으면 건너뛰기
            if field_name is None:
                continue
            
            try:
                value = evaluator.eval_expression(field_name)
                
                # 형식 지정이 있는 경우 처리
                if format_spec:
                    value = format(value, format_spec)
                
                # 변환 지정자가 있는 경우 처리
                if conversion == 's':
                    value = str(value)
                elif conversion == 'r':
                    value = repr(value)
                elif conversion == 'a':
                    value = ascii(value)
                
                result_parts.append(str(value))
            
            except Exception as e:
                logger.error(f"필드 '{field_name}' 평가 중 오류: {str(e)}")
                result_parts.append(f"[오류: {str(e)}]")
        
        return ''.join(result_parts)
        
    except Exception as e:
        logger.error(f"템플릿 평가 중 오류: {str(e)}")
        return f"템플릿 평가 중 오류: {str(e)}"

def compute_fstring(fstring: str, data: Union[List[Dict[str, Any]], pd.DataFrame]) -> str:
    """f-string 템플릿을 계산합니다.
    Returns:
        계산 결과과 반영된 문자열
    """
    try:
        result = evaluate_fstring(fstring, data)
        
        # 결과 로깅
        logger.info(f"템플릿 평가 결과: {result[:100]}..." if len(result) > 100 else result)
        
        # 오류 검사
        if any(error_msg in result for error_msg in ["Error: ", "Error in", "오류: "]):
            logger.warning(f"템플릿 평가 중 오류 감지: {result}")
            return (
                "요청주신 질문에 대한 데이터는 아래 표와 같습니다.\n\n"
            )
            
        if "Division by zero" in result:
            logger.warning("0으로 나누기 오류 감지")
            return (
                "요청주신 질문을 처리하는 과정에서 0으로 나눠야 하는 상황이 발생했습니다. "
                "이는 불가능하므로, 질문 혹은 데이터를 확인해주시면 감사하겠습니다.\n\n"
            )
            
        return result
        
    except Exception as e:
        logger.error(f"템플릿 평가 중 예외 발생: {str(e)}")
        return f"템플릿 평가 중 오류가 발생했습니다: {str(e)}"