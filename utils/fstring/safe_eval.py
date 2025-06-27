import ast
import re
import pandas as pd
from typing import Any, Dict, List, Union
from utils.logger import setup_logger

from utils.fstring.allowed_list import (
    ALLOWED_OPERATORS, 
    ALLOWED_DF_METHODS, 
    ALLOWED_BUILTINS, 
    FUNCTION_ALIASES,
    ALLOWED_ATTRIBUTES
)

logger = setup_logger('calc_table')


class SafeExpressionEvaluator:
    """안전한 표현식 평가를 위한 클래스"""
    def __init__(self, data: Union[List[Dict[str, Any]], pd.DataFrame]):
        if isinstance(data, pd.DataFrame):
            logger.info("Converting DataFrame to list of dicts")
            self.data = data.to_dict('records')
        else:
            # 이중 중첩 구조 처리
            if (len(data) == 1 and isinstance(data[0], dict) and 
                any(isinstance(val, list) for val in data[0].values())):
                
                # 첫 번째 딕셔너리의 값들 중 리스트 찾기
                for key, val in data[0].items():
                    if isinstance(val, list) and all(isinstance(item, dict) for item in val):
                        data = val
                        break
            
            self.df = pd.DataFrame(data)
        
        # 컨텍스트 초기화
        self.context = {
            'df': self.df,
            **{col: self.df[col] for col in self.df.columns},
            **ALLOWED_BUILTINS,
        }
        
        for name, func in FUNCTION_ALIASES.items():
            self.context[name] = func
    
    def _eval_node(self, node: ast.AST) -> Any:
        """AST 노드를 안전하게 평가
        Args:
            node: 평가할 AST 노드
        Returns:
            평가 결과
        Raises:
            ValueError: 허용되지 않은 노드 유형이나 연산을 만난 경우
        """
        logger.info(f"Evaluating node: {type(node).__name__}")
        
        if isinstance(node, ast.Constant):
            logger.info(f"Node is Constant: {node.value}")
            return node.value
        elif isinstance(node, ast.Name):
            logger.info(f"Node is Name: {node.id}")
            if node.id in self.context:
                logger.info(f"Found value in context")
                return self.context[node.id]
            logger.warning(f"Name {node.id} not found in context")
            raise ValueError(f"허용되지 않은 변수: {node.id}")
        elif isinstance(node, ast.BinOp):
            logger.info(f"Node is BinOp: {type(node.op).__name__}")
            if not isinstance(node.op, tuple(ALLOWED_OPERATORS.keys())):
                raise ValueError(f"허용되지 않은 연산자: {type(node.op).__name__}")
            
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            
            # 연산 결과가 숫자인 경우 포맷팅 적용
            result = ALLOWED_OPERATORS[type(node.op)](left, right)
            if isinstance(result, (int, float)):
                # 컬럼 이름 추출 (가능한 경우)
                column = None
                if isinstance(node.left, ast.Name) and node.left.id in self.df.columns:
                    column = node.left.id
                elif isinstance(node.right, ast.Name) and node.right.id in self.df.columns:
                    column = node.right.id
                
                logger.info(f"Operation result: {result}")
                return result
            return result
        
        # 속성 접근 (예: df.shape)
        elif isinstance(node, ast.Attribute):
            obj = self._eval_node(node.value)
            attr = node.attr
            
            # DataFrame/Series 메서드 호출 체크
            if isinstance(obj, (pd.DataFrame, pd.Series)) and attr in ALLOWED_DF_METHODS:
                logger.info(f"Calling DataFrame method: {attr}")
                return getattr(obj, attr)
            
            # numpy.ndarray 메서드 접근 허용 (unique 결과)
            elif hasattr(obj, '__class__') and hasattr(obj.__class__, '__module__') and obj.__class__.__module__ == 'numpy':
                if attr in ['tolist']:
                    logger.info(f"Calling numpy method: {attr}")
                    return getattr(obj, attr)
            
            # 일반 속성 접근 체크
            elif attr in ALLOWED_ATTRIBUTES:
                logger.info(f"Accessing attribute: {attr}")
                return getattr(obj, attr)
            
            else:
                logger.error(f"속성 '{attr}'는 허용되지 않았습니다")
                raise ValueError(f"속성 '{attr}'는 허용되지 않았습니다")
        
        # 비교 연산 (a > b, a == b 등)
        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left)
            
            # 모든 비교 결과가 True여야 함
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator)
                
                # in, not in 연산자 처리
                if isinstance(op, ast.In):
                    result = left in right
                elif isinstance(op, ast.NotIn):
                    result = left not in right
                elif type(op) in ALLOWED_OPERATORS:
                    result = ALLOWED_OPERATORS[type(op)](left, right)
                else:
                    logger.error(f"비교 연산자 {type(op).__name__}는 허용되지 않았습니다")
                    raise ValueError(f"비교 연산자 {type(op).__name__}는 허용되지 않았습니다")

                if isinstance(result, pd.Series):
                    return result

                if not result:
                    return False
                left = right
            
            return True
        
        # 인덱싱 (df['column'] 또는 df[0])
        elif isinstance(node, ast.Subscript):
            container = self._eval_node(node.value)
            
            # AST 버전에 따른 분기 처리
            if hasattr(node, 'slice') and isinstance(node.slice, ast.AST):
                # Python 3.9+ 버전
                idx = self._eval_node(node.slice)
            else:
                # 이전 버전
                idx = node.slice
            
            # 문자열 리터럴은 문자열로 변환 (ast가 Constant로 파싱)
            if isinstance(idx, ast.Constant) and isinstance(idx.value, str):
                idx = idx.value
                
            # 슬라이싱 객체 처리
            if isinstance(idx, ast.Slice):
                start = self._eval_node(idx.lower) if idx.lower else None
                stop = self._eval_node(idx.upper) if idx.upper else None
                step = self._eval_node(idx.step) if idx.step else None
                return container[slice(start, stop, step)]
                
            # DataFrame에 불리언 시리즈로 인덱싱하는 경우
            if isinstance(container, pd.DataFrame) and isinstance(idx, pd.Series) and idx.dtype == 'bool':
                return container[idx.values]
                
            return container[idx]
        
        # 함수 호출 (len(df), df.sum() 등)
        elif isinstance(node, ast.Call):
            logger.info(f"Node is Call: {node.func.id if isinstance(node.func, ast.Name) else type(node.func).__name__}")
            
            # 함수 객체 가져오기
            if isinstance(node.func, ast.Name):
                func = self._eval_node(node.func)
            elif isinstance(node.func, ast.Attribute):
                # 메서드 호출 처리 (예: df['acct_no'].count())
                obj = self._eval_node(node.func.value)
                method_name = node.func.attr
                logger.info(f"Method call: {method_name} on {type(obj).__name__}")
                
                if hasattr(obj, method_name):
                    func = getattr(obj, method_name)
                else:
                    logger.error(f"Method {method_name} not found on {type(obj).__name__}")
                    raise ValueError(f"Method {method_name} not found on {type(obj).__name__}")
            else:
                logger.error(f"Unsupported function type: {type(node.func).__name__}")
                raise ValueError(f"Unsupported function type: {type(node.func).__name__}")
            
            # 인자 평가
            args = [self._eval_node(arg) for arg in node.args]
            kwargs = {kw.arg: self._eval_node(kw.value) for kw in node.keywords}
            
            logger.info(f"Calling function with args: {args} and kwargs: {kwargs}")
            return func(*args, **kwargs)
        
        # 리스트 [1, 2, 3]
        elif isinstance(node, ast.List):
            logger.info("Node is List, evaluating elements")
            return [self._eval_node(elt) for elt in node.elts]
        
        # 튜플 (1, 2, 3)
        elif isinstance(node, ast.Tuple):
            logger.info("Node is Tuple, evaluating elements")
            return tuple(self._eval_node(elt) for elt in node.elts)
        
        # 딕셔너리 {'a': 1, 'b': 2}
        elif isinstance(node, ast.Dict):
            logger.info("Node is Dict, evaluating keys and values")
            keys = [self._eval_node(k) if k is not None else None for k in node.keys]
            values = [self._eval_node(v) for v in node.values]
            return dict(zip(keys, values))
        
        # 불리언 연산 (and, or, not)
        elif isinstance(node, ast.BoolOp):
            logger.info("Node is BoolOp, evaluating values")
            values = [self._eval_node(val) for val in node.values]
            
            if isinstance(node.op, ast.And):
                logger.info("Applying and operation")
                return all(values)
            elif isinstance(node.op, ast.Or):
                logger.info("Applying or operation")
                return any(values)
            else:
                logger.error(f"불리언 연산자 {type(node.op).__name__}는 허용되지 않았습니다")
                raise ValueError(f"불리언 연산자 {type(node.op).__name__}는 허용되지 않았습니다")
        
        # 단항 연산 (+x, -x, not x)
        elif isinstance(node, ast.UnaryOp):
            logger.info(f"Node is UnaryOp: {type(node.op).__name__}")
            operand = self._eval_node(node.operand)
            
            if isinstance(node.op, ast.Not):
                logger.info("Applying not operation")
                return not operand
            elif isinstance(node.op, ast.USub):
                logger.info("Applying unary minus operation")
                return -operand
            elif isinstance(node.op, ast.UAdd):
                logger.info("Applying unary plus operation")
                return +operand
            else:
                logger.error(f"단항 연산자 {type(node.op).__name__}는 허용되지 않았습니다")
                raise ValueError(f"단항 연산자 {type(node.op).__name__}는 허용되지 않았습니다")
                
        # 조건식 (a if condition else b)
        elif isinstance(node, ast.IfExp):
            logger.info("Node is IfExp, evaluating condition")
            condition = self._eval_node(node.test)
            return self._eval_node(node.body) if condition else self._eval_node(node.orelse)
        
        # 리스트 컴프리헨션 [x for x in iterable]
        elif isinstance(node, ast.ListComp):
            # 제너레이터 대신 리스트 직접 생성
            logger.info("Node is ListComp, evaluating elements")
            result = []
            elt = node.elt
            generators = node.generators
            
            def eval_generator(generators, idx=0, context_updates=None):
                if context_updates is None:
                    context_updates = {}
                
                if idx >= len(generators):
                    # 모든 제너레이터 처리 완료, 결과 계산
                    tmp_context = self.context.copy()
                    tmp_context.update(context_updates)
                    old_context = self.context
                    try:
                        self.context = tmp_context
                        result.append(self._eval_node(elt))
                    finally:
                        self.context = old_context
                    return
                
                # 현재 제너레이터 처리
                gen = generators[idx]
                iter_var = gen.target.id if isinstance(gen.target, ast.Name) else None
                if iter_var is None:
                    logger.error("복잡한 할당 타깃은 허용되지 않습니다")
                    raise ValueError("복잡한 할당 타깃은 허용되지 않습니다")
                
                iterator = self._eval_node(gen.iter)
                for val in iterator:
                    new_updates = context_updates.copy()
                    new_updates[iter_var] = val
                    
                    # if 조건 확인
                    ifs_ok = True
                    for if_clause in gen.ifs:
                        tmp_context = self.context.copy()
                        tmp_context.update(new_updates)
                        old_context = self.context
                        try:
                            self.context = tmp_context
                            if not self._eval_node(if_clause):
                                ifs_ok = False
                                break
                        finally:
                            self.context = old_context
                    
                    if ifs_ok:
                        eval_generator(generators, idx + 1, new_updates)
            
            eval_generator(generators)
            return result
        
        else:
            logger.error(f"표현식 유형 {type(node).__name__}는 허용되지 않았습니다")
            raise ValueError(f"표현식 유형 {type(node).__name__}는 허용되지 않았습니다")
    
    def eval_expression(self, expr: str) -> Any:
        """문자열 표현식을 안전하게 평가
        Args:
            expr: 평가할 표현식 문자열            
        Returns:
            평가 결과
        Raises:
            ValueError: 허용되지 않은 노드 유형이나 연산을 만난 경우
        """
        logger.info(f"Evaluating expression: {expr}")
        
        try:
            # 문자열 정규화
            expr = expr.strip()
            
            # pandas 불리언 인덱싱 특수 처리
            if re.search(r'df\[df\[.*?]==.*?\]', expr):
                # 이 패턴을 처리하기 위한 특별 로직
                match = re.search(r'df\[df\[(.*?)\]==(.*?)\]', expr)
                if match:
                    col_name = match.group(1).strip(" '\"")
                    val = match.group(2).strip()
                    # 따옴표 제거
                    if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
                        val = val[1:-1]
                    
                    # 필터링된 DataFrame 반환
                    return self.df[self.df[col_name] == val]
            
            # 사용자 정의 함수 패턴 처리
            for alias, replacement in [
                (r'count\((\w+)\)', r'len(df["\1"].dropna())'),
                (r'average\((\w+)\)', r'df["\1"].mean()'),
                (r'unique\((\w+)\)', r'df["\1"].unique()'),
                (r'list\((\w+)\)', r'df["\1"].tolist()'),
            ]:
                expr = re.sub(alias, replacement, expr)
            
            # AST 파싱 및 평가
            tree = ast.parse(expr, mode='eval')
            logger.info(f"AST tree: {ast.dump(tree, include_attributes=True)}")
            result = self._eval_node(tree.body)
            logger.info(f"Final evaluation result: {result}")
            return result
        
        except (SyntaxError, ValueError) as e:
            # 오류 메시지를 사용자 친화적으로 가공
            logger.error(f"Error evaluating expression: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"표현식 '{expr}' 평가 중 오류: {str(e)}"