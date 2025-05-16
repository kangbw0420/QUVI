from dataclasses import dataclass
from typing import Set

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

@dataclass
class QueryInfo:
    """SQL 쿼리의 구조 정보를 담는 클래스"""
    has_union: bool = False
    has_subquery: bool = False
    has_joins: bool = False
    join_types: Set[str] = None  # INNER, LEFT, RIGHT, FULL 등
    table_names: Set[str] = None  # 쿼리에서 참조된 테이블명들
    subquery_count: int = 0  # 서브쿼리 개수

class QueryClassifier:
    """SQL 쿼리의 구조를 분석하는 클래스"""
    
    @staticmethod
    def classify_query(query: str) -> QueryInfo:
        """주어진 SQL 쿼리의 구조를 분석하여 QueryInfo 객체 반환"""
        try:
            # 쿼리 파싱
            ast = sqlglot.parse_one(query, dialect='postgres')
            
            # 기본 QueryInfo 객체 생성
            info = QueryInfo(
                join_types=set(),
                table_names=set()
            )
            
            # AST 순회하며 구조 분석
            QueryClassifier._analyze_node(ast, info)
            
            return info
            
        except ParseError as e:
            # 파싱 실패 시 기본값으로 보수적 처리
            return QueryInfo(
                has_subquery=True,  # 파싱 실패 시 서브쿼리 있다고 가정
                join_types=set(),
                table_names=set()
            )
        except Exception as e:
            # 기타 예외 발생 시도 보수적 처리
            return QueryInfo(
                has_subquery=True,
                join_types=set(),
                table_names=set()
            )

    @staticmethod
    def _analyze_node(node: exp.Expression, info: QueryInfo) -> None:
        """재귀적으로 AST 노드를 분석하여 QueryInfo 업데이트"""
        
        # UNION 체크
        if isinstance(node, exp.Union):
            info.has_union = True
            # UNION의 양쪽 부분도 재귀적으로 분석
            QueryClassifier._analyze_node(node.left, info)
            QueryClassifier._analyze_node(node.right, info)
            return

        # 서브쿼리 체크
        if isinstance(node, exp.Subquery):
            info.has_subquery = True
            info.subquery_count += 1
            QueryClassifier._analyze_node(node.this, info)

        # JOIN 체크
        if isinstance(node, exp.Join):
            info.has_joins = True
            # JOIN 타입 추가 (INNER, LEFT, RIGHT, FULL 등)
            if node.side:  # side가 None이면 INNER JOIN
                info.join_types.add(node.side.upper())
            else:
                info.join_types.add('INNER')

        # 테이블명 수집
        if isinstance(node, exp.Table):
            # 테이블 이름을 집합에 추가
            info.table_names.add(node.name)

        # 노드의 자식들도 재귀적으로 분석
        for child in node.walk():
            if child is not node:  # 자기 자신은 제외
                QueryClassifier._analyze_node(child, info)

    @staticmethod
    def has_subquery(query: str) -> bool:
        """쿼리에 서브쿼리가 있는지 확인"""
        try:
            info = QueryClassifier.classify_query(query)
            return info.has_subquery
        except Exception:
            # 에러 발생 시 보수적으로 True 반환
            return True

    @staticmethod
    def has_union(query: str) -> bool:
        """쿼리에 UNION이 있는지 확인"""
        try:
            info = QueryClassifier.classify_query(query)
            return info.has_union
        except Exception:
            # 에러 발생 시 보수적으로 False 반환
            return False

    @staticmethod
    def get_referenced_tables(query: str) -> Set[str]:
        """쿼리에서 참조된 모든 테이블명 추출"""
        try:
            info = QueryClassifier.classify_query(query)
            return info.table_names
        except Exception:
            return set()

    @staticmethod
    def get_join_types(query: str) -> Set[str]:
        """쿼리에서 사용된 모든 JOIN 타입 추출"""
        try:
            info = QueryClassifier.classify_query(query)
            return info.join_types
        except Exception:
            return set()