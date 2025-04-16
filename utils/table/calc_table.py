from typing import Dict, List, Any, Union
import pandas as pd

from utils.logger import setup_logger
from utils.table.template_eval import TemplateEvaluator

logger = setup_logger('calc_table')


def compute_template(template: str, data: Union[List[Dict[str, Any]], pd.DataFrame], 
                    template_type: str = 'fstring') -> str:
    """
    주어진 템플릿 형식에 따라 템플릿을 평가합니다.
    
    Args:
        template: 평가할 템플릿 문자열
        data: 표현식 평가에 사용할 데이터
        template_type: 템플릿 유형 ('fstring', 향후 'jinja' 등 확장 가능)
        
    Returns:
        평가된 결과 문자열
    """
    
    
    try:
        # 템플릿 유형에 맞는 평가기 클래스 가져오기
        evaluator_class = TemplateEvaluator.get_evaluator(template_type)
        
        # 평가기 인스턴스 생성 및 템플릿 평가
        evaluator = evaluator_class(data)
        result = evaluator.evaluate(template)
        
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