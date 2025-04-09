import ast
import operator
import re
import pandas as pd
from string import Formatter
from typing import List, Dict, Any, Union


class SafeExpressionEvaluator:
    """안전한 표현식 평가를 위한 클래스"""
    
    # 허용된 연산자 및 함수 목록
    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
    }
    
    # 허용된 DataFrame/Series 메서드
    ALLOWED_DF_METHODS = {
        'sum', 'mean', 'count', 'min', 'max', 'median', 'std', 'var', 
        'describe', 'info', 'head', 'tail', 'unique', 'nunique', 'value_counts',
        'tolist', 'to_list', 'shape', 'size', 'apply', 'map', 'iloc', 'loc',
        'dtypes', 'drop', 'dropna', 'fillna', 'isna', 'isnull', 'notna',
        'notnull', 'reset_index', 'set_index', 'sort_values', 'sort_index',
        'groupby', 'copy', 'all', 'any', 'filter', 'idxmax', 'idxmin',
        'sample', 'shift', 'first', 'last', 'rolling', 'to_dict', 'values',
        'agg', 'aggregate', 'groups'
    }
    
    # 허용된 내장 함수
    ALLOWED_BUILTINS = {
        'len': len,
        'sum': sum,
        'int': int,
        'float': float,
        'str': str,
        'bool': bool,
        'list': list,
        'dict': dict,
        'set': set,
        'tuple': tuple,
        'abs': abs,
        'all': all,
        'any': any,
        'min': min,
        'max': max,
        'round': round,
        'sorted': sorted,
        'zip': zip,
        'map': map,
        'filter': filter,
        'enumerate': enumerate,
    }
    
    # 허용된 속성 접근
    ALLOWED_ATTRIBUTES = {
        'shape', 'size', 'index', 'columns', 'values', 'T'
    }
    
    # 특수 함수 매핑
    FUNCTION_ALIASES = {
        'count': lambda column: len(column.dropna()),
        'average': lambda column: column.mean(),
        'unique': lambda column: column.unique(),
        'list': lambda column: column.tolist(),
    }
    
    def __init__(self, data: Union[List[Dict[str, Any]], pd.DataFrame]):
        """
        안전한 표현식 평가기 초기화
        
        Args:
            data: 데이터프레임이나 딕셔너리 리스트
        """
        # 데이터프레임 변환
        if isinstance(data, pd.DataFrame):
            self.df = data
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
            **self.ALLOWED_BUILTINS,  # 허용된 내장 함수 추가
        }
        
        for name, func in self.FUNCTION_ALIASES.items():
            self.context[name] = func
    
    def _eval_node(self, node: ast.AST) -> Any:
        """
        AST 노드를 안전하게 평가
        
        Args:
            node: 평가할 AST 노드
            
        Returns:
            평가 결과
            
        Raises:
            ValueError: 허용되지 않은 노드 유형이나 연산을 만난 경우
        """
        # 리터럴 (숫자, 문자열 등)
        if isinstance(node, ast.Constant):
            return node.value
        
        # 변수 이름
        elif isinstance(node, ast.Name):
            if node.id in self.context:
                return self.context[node.id]
            else:
                raise ValueError(f"변수 '{node.id}'는 허용되지 않거나 정의되지 않았습니다")
        
        # 속성 접근 (예: df.shape)
        elif isinstance(node, ast.Attribute):
            obj = self._eval_node(node.value)
            attr = node.attr
            
            # DataFrame/Series 메서드 호출 체크
            if isinstance(obj, (pd.DataFrame, pd.Series)) and attr in self.ALLOWED_DF_METHODS:
                return getattr(obj, attr)
            
            # numpy.ndarray 메서드 접근 허용 (unique 결과)
            elif hasattr(obj, '__class__') and hasattr(obj.__class__, '__module__') and obj.__class__.__module__ == 'numpy':
                if attr in ['tolist']:
                    return getattr(obj, attr)
            
            # 일반 속성 접근 체크
            elif attr in self.ALLOWED_ATTRIBUTES:
                return getattr(obj, attr)
            
            else:
                raise ValueError(f"속성 '{attr}'는 허용되지 않았습니다")
        
        # 이항 연산 (a + b, a * b 등)
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            
            if type(node.op) in self.ALLOWED_OPERATORS:
                return self.ALLOWED_OPERATORS[type(node.op)](left, right)
            else:
                raise ValueError(f"연산자 {type(node.op).__name__}는 허용되지 않았습니다")
        
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
                elif type(op) in self.ALLOWED_OPERATORS:
                    result = self.ALLOWED_OPERATORS[type(op)](left, right)
                else:
                    raise ValueError(f"비교 연산자 {type(op).__name__}는 허용되지 않았습니다")
                
                if not result:
                    return False
                left = right
            
            return True
        
        # 인덱싱 (df['column'] 또는 df[0])
        elif isinstance(node, ast.Subscript):
            container = self._eval_node(node.value)
            
            idx = self._eval_node(node.slice)
            
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
            func = self._eval_node(node.func)
            args = [self._eval_node(arg) for arg in node.args]
            kwargs = {kw.arg: self._eval_node(kw.value) for kw in node.keywords}
            
            # 내장 함수인지 확인
            if func.__name__ in self.ALLOWED_BUILTINS or func in self.ALLOWED_BUILTINS.values():
                return func(*args, **kwargs)
            
            # 별칭 함수인지 확인
            elif any(func == alias_func for alias_func in self.FUNCTION_ALIASES.values()):
                return func(*args, **kwargs)
            
            # pandas 메서드인지 확인
            elif hasattr(func, '__self__') and isinstance(func.__self__, (pd.DataFrame, pd.Series)):
                method_name = func.__name__
                if method_name in self.ALLOWED_DF_METHODS:
                    return func(*args, **kwargs)
                else:
                    raise ValueError(f"메서드 '{method_name}'는 허용되지 않았습니다")
            
            else:
                raise ValueError(f"함수 '{func.__name__}'는 허용되지 않았습니다")
        
        # 리스트 [1, 2, 3]
        elif isinstance(node, ast.List):
            return [self._eval_node(elt) for elt in node.elts]
        
        # 튜플 (1, 2, 3)
        elif isinstance(node, ast.Tuple):
            return tuple(self._eval_node(elt) for elt in node.elts)
        
        # 딕셔너리 {'a': 1, 'b': 2}
        elif isinstance(node, ast.Dict):
            keys = [self._eval_node(k) if k is not None else None for k in node.keys]
            values = [self._eval_node(v) for v in node.values]
            return dict(zip(keys, values))
        
        # 불리언 연산 (and, or, not)
        elif isinstance(node, ast.BoolOp):
            values = [self._eval_node(val) for val in node.values]
            
            if isinstance(node.op, ast.And):
                return all(values)
            elif isinstance(node.op, ast.Or):
                return any(values)
            else:
                raise ValueError(f"불리언 연산자 {type(node.op).__name__}는 허용되지 않았습니다")
        
        # 단항 연산 (+x, -x, not x)
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            
            if isinstance(node.op, ast.Not):
                return not operand
            elif isinstance(node.op, ast.USub):
                return -operand
            elif isinstance(node.op, ast.UAdd):
                return +operand
            else:
                raise ValueError(f"단항 연산자 {type(node.op).__name__}는 허용되지 않았습니다")
                
        # 조건식 (a if condition else b)
        elif isinstance(node, ast.IfExp):
            condition = self._eval_node(node.test)
            return self._eval_node(node.body) if condition else self._eval_node(node.orelse)
        
        # 리스트 컴프리헨션 [x for x in iterable]
        elif isinstance(node, ast.ListComp):
            # 제너레이터 대신 리스트 직접 생성
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
            raise ValueError(f"표현식 유형 {type(node).__name__}는 허용되지 않았습니다")
    
    def eval_expression(self, expr: str) -> Any:
        """
        문자열 표현식을 안전하게 평가
        
        Args:
            expr: 평가할 표현식 문자열
            
        Returns:
            평가 결과
            
        Raises:
            ValueError: 허용되지 않은 노드 유형이나 연산을 만난 경우
        """
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
            result = self._eval_node(tree.body)
            return result
        
        except (SyntaxError, ValueError) as e:
            # 오류 메시지를 사용자 친화적으로 가공
            return f"표현식 '{expr}' 평가 중 오류: {str(e)}"
    
    def eval_fstring(self, fstring_template: str) -> str:
        """
        f-string 형식 템플릿 평가
        
        Args:
            fstring_template: f-string 형식 템플릿
            
        Returns:
            평가된 문자열
        """
        # 표현식 형식 확인 및 추출
        result_parts = []
        formatter = Formatter()
        
        for literal_text, field_name, format_spec, conversion in formatter.parse(fstring_template):
            # 리터럴 텍스트 추가
            result_parts.append(literal_text)
            
            # 표현식 필드가 없으면 건너뛰기
            if field_name is None:
                continue
            
            # 표현식 평가
            try:
                value = self.eval_expression(field_name)
                
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
                result_parts.append(f"[오류: {str(e)}]")
        
        return ''.join(result_parts)


def eval_fstring_template(fstring: str, data: Union[List[Dict[str, Any]], pd.DataFrame]) -> str:
    """
    f-string 템플릿을 안전하게 평가
    
    Args:
        fstring: f-string 형식 템플릿
        data: 데이터프레임이나 딕셔너리 리스트
        
    Returns:
        평가된 문자열
    """
    try:
        # f-string 마커 제거 (f"..." 또는 f'...')
        if fstring.startswith('f"') and fstring.endswith('"'):
            fstring = fstring[2:-1]
        elif fstring.startswith("f'") and fstring.endswith("'"):
            fstring = fstring[2:-1]
        
        evaluator = SafeExpressionEvaluator(data)
        return evaluator.eval_fstring(fstring)
    
    except Exception as e:
        return f"f-string 평가 중 오류: {str(e)}"