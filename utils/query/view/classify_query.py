import re

import sqlglot
from sqlglot.errors import ParseError
from sqlglot.expressions import Subquery

def has_subquery(query: str) -> bool:
    """
    SQL 쿼리에 서브쿼리가 포함되어 있는지 확인합니다.
    sqlglot 라이브러리를 사용하여 AST를 생성하고, Subquery 노드를 탐색합니다.
    """
    try:
        expression = sqlglot.parse_one(query, dialect='postgres')
        for node in expression.walk():
            if isinstance(node, Subquery):
                return True
        return False
    except ParseError:
        # 파싱 오류 발생 시 안전하게 True 반환 (수정하지 않음)
        return True
    except Exception:
        # 기타 예외 발생 시도 안전하게 True 반환
        return True

def has_union(query: str) -> bool:
    """
    SQL 쿼리에 UNION 연산자가 포함되어 있는지 확인합니다.
    """
    # 대소문자 구분 없이 UNION 키워드 검색
    return bool(re.search(r'\bUNION\b', query, re.IGNORECASE))