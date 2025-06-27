import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from utils.query.view.classify_query import QueryClassifier

@dataclass
class ViewFunction:
    base_name: str
    first_param: str
    second_param: str
    third_param: str
    from_date: str
    to_date: str
    alias: Optional[str] = None
    query_id: Optional[str] = None  # 각 쿼리/서브쿼리의 고유 ID

class ViewTableTransformer:
    """SQL query transformer for view table functionality"""
    def __init__(self, user_info: Tuple[str, str],
                 view_com: str, date_info: Tuple[str, str], flags: Dict[str, bool]):
        self.first_param = user_info[1]  # use_intt_id
        self.second_param = user_info[0]  # user_id
        self.third_param = view_com
        self.from_date = date_info[0]
        self.to_date = date_info[1]
        self.flags = flags
        self.classifier = QueryClassifier()
        self.query_counter = 0  # 서브쿼리에 고유 ID 부여를 위한 카운터

    def transform_query(self, query: str) -> str:
        """
        Transform SQL query by adding view table functions
        Returns:
            str: 변환된 SQL 쿼리
        """
        try:
            # initialize query counter
            self.query_counter = 0
            
            # parsing query
            ast = sqlglot.parse_one(query, dialect='postgres')
            
            # analyze query structure
            query_info = self.classifier.classify_query(query)
            
            if query_info.has_union:
                transformed_ast = self._handle_union_query(ast)
            else:
                transformed_ast = self._handle_single_query(ast)
            
            # 변환된 SQL 문자열 반환
            return transformed_ast.sql(dialect='postgres')
            
        except ParseError as e:
            print(f"Parse error: {e}")
            return query
        except Exception as e:
            print(f"Unexpected error: {e}")
            return query

    def _handle_union_query(self, ast: exp.Union) -> exp.Expression:
        """UNION 쿼리 처리        
        Args:
            ast: SQL AST의 Union 노드
        Returns:
            변환된 Union 노드
        """
        # 왼쪽과 오른쪽 부분 쿼리 처리
        transformed_left = self._handle_single_query(ast.left)
        transformed_right = self._handle_single_query(ast.right)
        
        # 변환된 UNION 반환
        return exp.Union(
            this=transformed_left,
            expression=transformed_right,
            distinct=False
        )

    def _handle_single_query(self, ast: exp.Expression) -> exp.Expression:
        """단일 SELECT 쿼리 처리
        Args:
            ast: SQL AST의 Select 노드
        Returns:
            변환된 Select 노드
        """
        def transform_table(node: exp.Expression) -> exp.Expression:
            """테이블 참조를 뷰 함수 호출로 변환"""
            if isinstance(node, exp.Table):
                if node.name.startswith('aicfo_get_all_'):
                    view_func = self._create_view_function(
                        ViewFunction(
                            base_name=node.name,  
                            first_param=self.first_param,
                            second_param=self.second_param,
                            third_param=self.third_param,
                            from_date=self.from_date,
                            to_date=self.to_date,
                            alias=node.alias
                        )
                    )
                    return view_func
            return node

        # 먼저 테이블 참조 변환
        transformed_ast = ast.transform(transform_table)
        
        # 서브쿼리 처리 (테이블 참조 변환 후)
        if self.classifier.has_subquery(ast.sql(dialect='postgres')):
            transformed_ast = self._handle_subqueries(transformed_ast)
        
        return transformed_ast

    def _handle_subqueries(self, ast: exp.Expression) -> exp.Expression:
        """AST 내의 서브쿼리 처리"""
        def transform_subquery(node: exp.Expression) -> exp.Expression:
            if isinstance(node, exp.Subquery):
                # 서브쿼리에 고유 ID 부여
                self.query_counter += 1
                
                # 서브쿼리 SQL 문자열 가져오기
                subquery_sql = node.this.sql(dialect='postgres')
                
                # 함수 호출 패턴에서 날짜 부분 직접 교체
                pattern = r"AICFO_GET_ALL_\w+\('[^']*', '[^']*', '[^']*', '(\d+)', '(\d+)'\)"
                replacement = lambda m: m.group(0).replace(
                    f"'{m.group(1)}', '{m.group(2)}'", 
                    f"'{self.from_date}', '{self.to_date}'"
                )
                modified_sql = re.sub(pattern, replacement, subquery_sql)
                
                if modified_sql != subquery_sql:
                    try:
                        # 수정된 SQL 파싱해서 새 서브쿼리 생성
                        modified_subquery = sqlglot.parse_one(modified_sql, dialect='postgres')
                        return exp.Subquery(this=modified_subquery)
                    except Exception as e:
                        print(f"Error parsing modified SQL: {e}")
                
                return node
            return node

        # AST를 순회하며 서브쿼리 변환
        transformed_ast = ast.transform(transform_subquery)
        return transformed_ast

    def _create_view_function(self, view_func: ViewFunction) -> exp.Expression:
        """뷰 함수 호출 표현식 생성
        Args:
            view_func: 뷰 함수 정보
        Returns:
            함수 호출 AST 노드
        """
        func_call = exp.Anonymous(
            this=view_func.base_name,
            expressions=[
                exp.Literal.string(view_func.first_param),
                exp.Literal.string(view_func.second_param),
                exp.Literal.string(view_func.third_param),
                exp.Literal.string(view_func.from_date),
                exp.Literal.string(view_func.to_date)
            ]
        )
        
        # 별칭이 있으면 적용
        if view_func.alias:
            return exp.Alias(this=func_call, alias=view_func.alias)
        return func_call

    @staticmethod
    def _validate_query(query: str) -> bool:
        """쿼리가 변환 가능한지 검증
        Returns:
            bool: 변환 가능 여부
        """
        try:
            sqlglot.parse_one(query, dialect='postgres')
            return True
        except ParseError:
            return False

def view_table(query_ordered: str, company_id: str, 
               user_info: Tuple[str, str], date_info: Tuple[str, str], flags: dict) -> str:
    transformer = ViewTableTransformer(user_info, company_id, date_info, flags)
    return transformer.transform_query(query_ordered)