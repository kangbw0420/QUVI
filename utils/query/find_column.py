from typing import List, Dict

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from utils.logger import setup_logger

logger = setup_logger('find_column')

def find_column_conditions(query: str, column_name: str) -> List[Dict]:
    """SQL 쿼리에서 특정 컬럼의 조건을 찾아 반환
    
    Args:
        query: SQL 쿼리 문자열
        column_name: 찾을 컬럼 이름
        
    Returns:
        List[Dict]: 컬럼 조건 정보 리스트. 각 조건은 다음 정보를 포함:
            - type: 조건 타입 (EQ, Like, ILike 등)
            - value: 조건 값
            - node: 원본 AST 노드
    """
    try:
        ast = sqlglot.parse_one(query, dialect='postgres')
        return _find_column_conditions_in_ast(ast, column_name)
    except ParseError as e:
        logger.error(f"SQL parsing error in find_column_conditions: {e}")
        return []
    except Exception as e:
        logger.error(f"Error in find_column_conditions: {e}")
        return []

def _find_column_conditions_in_ast(ast: exp.Expression, column_name: str) -> List[Dict]:
    """AST에서 특정 컬럼의 조건을 찾아 반환
    
    Args:
        ast: SQL AST
        column_name: 찾을 컬럼 이름
        
    Returns:
        List[Dict]: 컬럼 조건 정보 리스트
    """
    conditions: List[Dict] = []
    visited_nodes = set()

    def process_node(node):
        # 이미 방문한 노드는 처리하지 않음
        node_id = id(node)
        if node_id in visited_nodes:
            return
        visited_nodes.add(node_id)

        # 컬럼 조건인지 확인
        if isinstance(node, (exp.EQ, exp.Like, exp.ILike)):
            if (isinstance(node.this, exp.Column) and
                node.this.name == column_name):
                # 값 추출
                if isinstance(node.expression, exp.Literal):
                    value = str(node.expression.this).strip("'%")
                else:
                    value = str(node.expression).strip("'%")

                # 조건 정보 저장
                conditions.append({
                    'type': type(node).__name__,
                    'value': value,
                    'node': node
                })

        # 자식 노드 처리
        for arg_name, arg_value in node.args.items():
            if isinstance(arg_value, exp.Expression):
                process_node(arg_value)
            elif isinstance(arg_value, list):
                for item in arg_value:
                    if isinstance(item, exp.Expression):
                        process_node(item)

    # 루트 노드부터 시작
    process_node(ast)
    return conditions 