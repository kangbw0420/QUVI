import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError
from datetime import datetime, timedelta

from typing_extensions import List

from utils.query.view.classify_query import QueryClassifier
from utils.query.view.extract_date import DateExtractor

@dataclass
class ViewFunction:
    base_name: str
    use_intt_id: str
    user_id: str
    view_com: str
    from_date: str
    to_date: str
    alias: Optional[str] = None
    query_id: Optional[str] = None  # 각 쿼리/서브쿼리의 고유 ID

class ViewTableTransformer:
    """SQL query transformer for view table functionality"""
    def __init__(self, selected_table: str, user_info: Tuple[str, str],
                 view_com: str, flags: Dict[str, bool]):
        self.selected_table = selected_table
        self.user_id, self.use_intt_id = user_info
        self.view_com = view_com
        self.flags = flags
        self.classifier = QueryClassifier()
        self.date_extractor = DateExtractor(selected_table)
        self.date_ranges = {}  # 쿼리 ID별 날짜 범위 저장
        self.query_counter = 0  # 서브쿼리에 고유 ID 부여를 위한 카운터

    def transform_query(self, query: str) -> Tuple[str, Dict[str, Tuple[str, str]]]:
        """
        Transform SQL query by adding view table functions
        Returns:
            Tuple[str, Dict[str, Tuple[str, str]]]: 
                - 변환된 SQL 쿼리
                - 쿼리 ID별 날짜 범위 정보 (from_date, to_date)
        """
        try:
            # initialize query counter
            self.query_counter = 0
            self.date_ranges = {}
            
            # parsing query
            ast = sqlglot.parse_one(query, dialect='postgres')
            
            # analyze query sturcture
            query_info = self.classifier.classify_query(query)
            
            if query_info.has_union:
                transformed_ast = self._handle_union_query(ast)
            else:
                query_id = "main"
                
                # 메인 쿼리의 날짜 범위 추출
                date_range = self.date_extractor.extract_dates(query)
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    from_date, to_date = date_range
                    self.date_ranges[query_id] = (from_date, to_date)
                    
                    # 미래 날짜 처리
                    if from_date > self.date_extractor.today_str or to_date > self.date_extractor.today_str:
                        self.flags["future_date"] = True
                else:
                    # 날짜 추출 실패 시 기본값 설정
                    today = self.date_extractor.today_str
                    self.date_ranges[query_id] = (today, today)
                
                # 쿼리 변환
                transformed_ast = self._handle_single_query(ast, query_id)
            
            # 변환된 SQL 문자열
            transformed_sql = transformed_ast.sql(dialect='postgres')
            
            # 변환된 SQL과 날짜 정보 반환
            return transformed_sql, self.date_ranges
            
        except ParseError as e:
            print(f"Parse error: {e}")
            # 파싱 실패 시 원본 쿼리와 기본 날짜 정보 반환
            today = self.date_extractor.today_str
            self.date_ranges["main"] = (today, today)
            return query, self.date_ranges
        except Exception as e:
            print(f"Unexpected error: {e}")
            # 기타 오류 처리
            today = self.date_extractor.today_str
            self.date_ranges["main"] = (today, today)
            return query, self.date_ranges

    def _handle_union_query(self, ast: exp.Union) -> exp.Expression:
        """UNION 쿼리 처리        
        Args:
            ast: SQL AST의 Union 노드
        Returns:
            변환된 Union 노드
        """
        # 왼쪽과 오른쪽 부분 쿼리에 ID 할당
        left_id = "left_union"
        right_id = "right_union"
        
        # 왼쪽 부분쿼리 처리
        left_query = ast.left.sql(dialect='postgres')
        left_dates = self.date_extractor.extract_dates(left_query)
        self.date_ranges[left_id] = left_dates
        transformed_left = self._handle_single_query(ast.left, left_id)
        
        # 오른쪽 부분쿼리 처리
        right_query = ast.right.sql(dialect='postgres')
        right_dates = self.date_extractor.extract_dates(right_query)
        self.date_ranges[right_id] = right_dates
        transformed_right = self._handle_single_query(ast.right, right_id)
        
        # 미래 날짜 처리
        for date_range in [left_dates, right_dates]:
            from_date, to_date = date_range
            if from_date > self.date_extractor.today_str or to_date > self.date_extractor.today_str:
                self.flags["future_date"] = True
        
        # 변환된 UNION 반환
        return exp.Union(
            this=transformed_left,
            expression=transformed_right,
            distinct=False
        )

    def _handle_single_query(self, ast: exp.Expression, query_id: str) -> exp.Expression:
        """단일 SELECT 쿼리 처리
        Args:
            ast: SQL AST의 Select 노드
            query_id: 쿼리 식별자
        Returns:
            변환된 Select 노드
        """
        # 현재 AST 노드에 대해서만 날짜 조건을 추출
        sql_query = ast.sql(dialect='postgres')
        try:
            from_date, to_date = self.date_extractor.extract_dates(sql_query, ast)
            
            # 날짜 정보 저장
            self.date_ranges[query_id] = (from_date, to_date)
            
            # 미래 날짜 처리
            if from_date > self.date_extractor.today_str or to_date > self.date_extractor.today_str:
                self.flags["future_date"] = True
                if from_date > self.date_extractor.today_str:
                    from_date = self.date_extractor.today_str
                if to_date > self.date_extractor.today_str:
                    to_date = self.date_extractor.today_str
                self.date_ranges[query_id] = (from_date, to_date)

        except Exception as e:
            print(f"Error extracting dates in _handle_single_query: {str(e)}")
            # 날짜 추출 실패 시 기본값 설정
            today = self.date_extractor.today_str
            self.date_ranges[query_id] = (today, today)
            from_date, to_date = today, today

        def transform_table(node: exp.Expression) -> exp.Expression:
            """테이블 참조를 뷰 함수 호출로 변환"""
            if isinstance(node, exp.Table):
                if node.name.startswith('aicfo_get_all_'):
                    # 해당 쿼리 ID의 날짜 정보 사용
                    current_from_date, current_to_date = self.date_ranges.get(query_id, (self.date_extractor.today_str, self.date_extractor.today_str))

                    view_func = self._create_view_function(
                        ViewFunction(
                            base_name=node.name,
                            use_intt_id=self.use_intt_id,
                            user_id=self.user_id,
                            view_com=self.view_com,
                            from_date=current_from_date,
                            to_date=current_to_date,
                            alias=node.alias,
                            query_id=query_id
                        )
                    )
                    return view_func
            # 그 외 노드는 그대로 반환
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
                subquery_id = f"subquery_{self.query_counter}"
                
                # 서브쿼리 SQL 추출
                subquery_sql = node.this.sql(dialect='postgres')
                
                # 서브쿼리만의 날짜 조건 추출
                conditions = self.date_extractor._extract_date_conditions(node.this)
                
                # 날짜 컬럼이 trsc_dt 또는 reg_dt인 조건만 확인
                date_conditions = [
                    condition for condition in conditions 
                    if condition.column in ['reg_dt', 'trsc_dt']
                ]
                
                # 초기화
                subquery_from_date = None
                subquery_to_date = None
                
                if date_conditions:
                    # 날짜 조건이 있는 경우 사용
                    condition = date_conditions[0]
                    
                    if condition.operator in ('GT', '>'):
                        # value의 다음날부터 today_str까지
                        subquery_from_date = (datetime.strptime(condition.value, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
                        subquery_to_date = self.date_extractor.today_str
                    elif condition.operator in ('GTE', '>='):
                        # value부터 today_str까지
                        subquery_from_date = condition.value
                        subquery_to_date = self.date_extractor.today_str
                    elif condition.operator == 'BETWEEN':
                        subquery_from_date = condition.value
                        subquery_to_date = condition.secondary_value
                    elif condition.operator in ('EQ', '='):
                        subquery_from_date = condition.value
                        subquery_to_date = condition.value
                    else:
                        # LT, LTE 등 다른 조건들 처리
                        subquery_from_date = "19700101"
                        subquery_to_date = condition.value

                    self.date_ranges[subquery_id] = (subquery_from_date, subquery_to_date)
                else:
                    # 서브쿼리에 날짜 조건이 없는 경우, 부모 쿼리의 날짜 범위 사용
                    parent_query_id = "main"  # 기본값
                    parent_dates = self.date_ranges.get(parent_query_id, (self.date_extractor.today_str, self.date_extractor.today_str))
                    subquery_from_date, subquery_to_date = parent_dates
                    self.date_ranges[subquery_id] = (subquery_from_date, subquery_to_date)
                
                # 미래 날짜 처리
                if subquery_from_date > self.date_extractor.today_str:
                    self.flags["future_date"] = True
                    subquery_from_date = self.date_extractor.today_str
                    self.date_ranges[subquery_id] = (subquery_from_date, subquery_to_date)
                
                # 서브쿼리 SQL 문자열 가져오기
                subquery_sql = node.this.sql(dialect='postgres')
                
                # 함수 호출 패턴에서 날짜 부분 직접 교체
                pattern = r"AICFO_GET_ALL_\w+\('[^']*', '[^']*', '[^']*', '(\d+)', '(\d+)'\)"
                replacement = lambda m: m.group(0).replace(
                    f"'{m.group(1)}', '{m.group(2)}'", 
                    f"'{subquery_from_date}', '{subquery_to_date}'"
                )
                modified_sql = re.sub(pattern, replacement, subquery_sql)
                
                if modified_sql != subquery_sql:
                    try:
                        # 수정된 SQL 파싱해서 새 서브쿼리 생성
                        modified_subquery = sqlglot.parse_one(modified_sql, dialect='postgres')
                        return exp.Subquery(this=modified_subquery)
                    except Exception as e:
                        print(f"Error parsing modified SQL: {e}")
                
                # 기존 방식으로도 시도
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
                exp.Literal.string(view_func.use_intt_id),
                exp.Literal.string(view_func.user_id),
                exp.Literal.string(view_func.view_com),
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

def view_table(query: str, selected_table: str,
               company_id: str, user_info: Tuple[str, str], flags: dict) -> Tuple[str, Dict[str, Tuple[str, str]]]:
    """
    view_table을 적용하여 최종 변환된 날짜정보와 쿼리를 반환
    
    Args:
        query_ordered: ORDER BY가 추가된 SQL 쿼리
        selected_table: 선택된 테이블 (amt, trsc, stock 등)
        company_id: 메인 회사명
        user_info: (user_id, use_intt_id) 튜플
        flags: 상태 플래그 딕셔너리 (미래 날짜 등)
        
    Returns:
        Tuple[str, Tuple[str, str]]: 변환된 SQL 쿼리와 메인 쿼리의 날짜 범위
    """
    transformer = ViewTableTransformer(
        selected_table=selected_table,
        user_info=user_info,
        view_com=company_id,
        flags=flags
    )
    
    # 쿼리 변환 및 날짜 정보 추출
    transformed_query, date_ranges = transformer.transform_query(query)

    return transformed_query, date_ranges