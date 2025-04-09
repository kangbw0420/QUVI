from abc import ABC, abstractmethod
from string import Formatter
import pandas as pd
from typing import Any, Dict, List, Union

from utils.table.expression_eval import SafeExpressionEvaluator
from utils.logger import setup_logger

logger = setup_logger('template_evaluator')

class TemplateEvaluator(ABC):
    """템플릿 평가를 위한 추상 기본 클래스"""
    
    def __init__(self, data: Union[List[Dict[str, Any]], pd.DataFrame]):
        """템플릿 평가기 초기화
        
        Args:
            data: 표현식 평가에 사용할 데이터
        """
        self.evaluator = SafeExpressionEvaluator(data)
        
    @abstractmethod
    def evaluate(self, template: str) -> str:
        """템플릿 문자열을 평가하여 결과 문자열 반환
        
        Args:
            template: 평가할 템플릿 문자열
            
        Returns:
            평가된 결과 문자열
        """
        pass
    
    @classmethod
    def get_evaluator(cls, template_type: str) -> 'TemplateEvaluator':
        """템플릿 유형에 맞는 평가기 인스턴스 반환
        
        Args:
            template_type: 템플릿 유형 ("fstring", "jinja", 등)
            
        Returns:
            해당 유형의 TemplateEvaluator 인스턴스
        """
        evaluator_map = {
            'fstring': FStringTemplateEvaluator,
        }
        
        if template_type in evaluator_map:
            return evaluator_map[template_type]
        else:
            raise ValueError(f"지원하지 않는 템플릿 유형: {template_type}")


class FStringTemplateEvaluator(TemplateEvaluator):
    """Python f-string 스타일 템플릿 평가기"""
    
    def evaluate(self, template: str) -> str:
        """f-string 형식의 템플릿 문자열을 평가하여 결과 문자열 반환
        
        Args:
            template: f-string 형식의 템플릿 문자열 (예: "이름: {df['name']}")
            
        Returns:
            평가된 결과 문자열
        """
        result_parts = []
        formatter = Formatter()
        
        try:
            for literal_text, field_name, format_spec, conversion in formatter.parse(template):
                # 리터럴 텍스트 추가
                result_parts.append(literal_text)
                
                # 표현식 필드가 없으면 건너뛰기
                if field_name is None:
                    continue
                
                try:
                    value = self.evaluator.eval_expression(field_name)
                    
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


def eval_fstring_template(template: str, data: Union[List[Dict[str, Any]], pd.DataFrame]) -> str:
    """Python f-string 형식의 템플릿 문자열을 평가하여 결과 문자열 반환
    
    Args:
        template: f-string 형식의 템플릿 문자열 (예: f"이름: {df['name']}")
        data: 표현식 평가에 사용할 데이터
        
    Returns:
        평가된 결과 문자열
    """
    try:
        # f-string 마커 제거 (f"..." 또는 f'...')
        if template.startswith('f"') and template.endswith('"'):
            template = template[2:-1]
        elif template.startswith("f'") and template.endswith("'"):
            template = template[2:-1]
        
        evaluator = FStringTemplateEvaluator(data)
        return evaluator.evaluate(template)
    
    except Exception as e:
        logger.error(f"f-string 평가 중 오류: {str(e)}")
        return f"f-string 평가 중 오류: {str(e)}"