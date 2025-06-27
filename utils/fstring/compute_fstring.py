from typing import Dict, List, Any, Union
import pandas as pd
from string import Formatter

from utils.logger import setup_logger
from utils.fstring.safe_eval import SafeExpressionEvaluator

logger = setup_logger('calc_table')

def compute_fstring(fstring: str, data: Union[List[Dict[str, Any]], pd.DataFrame]) -> str:
    """f-string 템플릿을 계산하고 결과를 반환합니다.
    Returns:
        계산 결과가 반영된 문자열
    """
    try:
        logger.info(f"Input f-string: {fstring}")
        
        # f-string 마커 제거 (f"..." 또는 f'...')
        if fstring.startswith('f"') and fstring.endswith('"'):
            fstring = fstring[2:-1]
        elif fstring.startswith("f'") and fstring.endswith("'"):
            fstring = fstring[2:-1]
            
        # 이중 중괄호를 단일 중괄호로 변환
        fstring = fstring.replace('{{', '{').replace('}}', '}')
        logger.info(f"Cleaned f-string: {fstring}")
        
        evaluator = SafeExpressionEvaluator(data)
        formatter = Formatter()
        result_parts = []
        
        # qv를 잘 다루기 위해서는 Formatter의 구성을 잘 알아야 함
        # literal_text: 중괄호 외부의 일반 텍스트
        # field_name: 중괄호 내부의 필드 이름
        # format_spec: 콜론 뒤에 오는 형식 지정자
        # conversion: 느낌표 뒤에 오는 변환 지정자
        for literal_text, field_name, format_spec, conversion in formatter.parse(fstring):
            logger.info(f"Processing format part - literal: {literal_text}, field: {field_name}, format: {format_spec}, conversion: {conversion}")
            
            # 리터럴 텍스트 추가
            result_parts.append(literal_text)
            
            if field_name is None:
                continue
            
            try:
                value = evaluator.eval_expression(field_name)
                logger.info(f"Expression result: {value} (type: {type(value)})")
                
                # 형식 지정이 있는 경우 처리
                if format_spec:
                    logger.info(f"Applying format spec: {format_spec}")
                    value = format(value, format_spec)
                    logger.info(f"Formatted value: {value}")
                
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
        
        result = ''.join(result_parts)
        
        # 오류 검사
        if any(error_msg in result for error_msg in ["Error", "오류"]):
            logger.warning(f"템플릿 평가 중 오류 감지: {result}")
            return "요청주신 질문에 대한 데이터는 아래 표와 같습니다.\n\n"
            
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