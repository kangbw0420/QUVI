import operator
import ast

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
    "shape", "size", "index", "columns", "values", "T"
}

# 특수 함수 매핑
FUNCTION_ALIASES = {
    "count": lambda column: len(column.dropna()),
    "average": lambda column: column.mean(),
    "unique": lambda column: column.unique(),
    "list": lambda column: column.tolist(),
}
