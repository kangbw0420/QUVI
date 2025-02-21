from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

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
            # 쿼리 카운터 초기화
            self.query_counter = 0
            self.date_ranges = {}
            
            # 쿼리 파싱
            ast = sqlglot.parse_one(query, dialect='postgres')
            
            # 쿼리 구조 분석
            query_info = self.classifier.classify_query(query)
            print(f"DEBUG: Query Info - has_union: {query_info.has_union}, has_subquery: {query_info.has_subquery}")
            
            # 쿼리 타입에 따라 처리
            if query_info.has_union:
                # UNION 쿼리 처리
                print("DEBUG: Processing UNION query")
                transformed_ast = self._handle_union_query(ast)
            else:
                # 일반 쿼리 처리
                query_id = "main"
                print(f"DEBUG: Processing regular query with ID: {query_id}")
                
                # 메인 쿼리의 날짜 범위 추출
                from_date, to_date = self.date_extractor.extract_dates(query)
                print(f"DEBUG: Main query date range: {from_date}, {to_date}")
                self.date_ranges[query_id] = (from_date, to_date)
                
                # 미래 날짜 처리
                if from_date > self.date_extractor.today_str or to_date > self.date_extractor.today_str:
                    print(f"DEBUG: Future date detected. Today: {self.date_extractor.today_str}, Dates: {from_date}, {to_date}")
                    self.flags["future_date"] = True
                
                # 쿼리 변환
                transformed_ast = self._handle_single_query(ast, query_id)
            
            # 변환된 SQL 문자열
            transformed_sql = transformed_ast.sql(dialect='postgres')
            print(f"DEBUG: Date ranges after transformation: {self.date_ranges}")
            print(f"DEBUG: Transformed Query: {transformed_sql}")
            
            # 변환된 SQL과 날짜 정보 반환
            return transformed_sql, self.date_ranges
            
        except ParseError as e:
            print(f"DEBUG: Parse error: {e}")
            # 파싱 실패 시 원본 쿼리와 기본 날짜 정보 반환
            today = self.date_extractor.today_str
            self.date_ranges["main"] = (today, today)
            return query, self.date_ranges
        except Exception as e:
            print(f"DEBUG: Unexpected error: {e}")
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
        print(f"DEBUG: Processing left union part: {left_query}")
        left_dates = self.date_extractor.extract_dates(left_query)
        print(f"DEBUG: Left union dates: {left_dates}")
        self.date_ranges[left_id] = left_dates
        transformed_left = self._handle_single_query(ast.left, left_id)
        
        # 오른쪽 부분쿼리 처리
        right_query = ast.right.sql(dialect='postgres')
        print(f"DEBUG: Processing right union part: {right_query}")
        right_dates = self.date_extractor.extract_dates(right_query)
        print(f"DEBUG: Right union dates: {right_dates}")
        self.date_ranges[right_id] = right_dates
        transformed_right = self._handle_single_query(ast.right, right_id)
        
        # 미래 날짜 처리
        for date_range in [left_dates, right_dates]:
            from_date, to_date = date_range
            if from_date > self.date_extractor.today_str or to_date > self.date_extractor.today_str:
                print(f"DEBUG: Future date in union. Today: {self.date_extractor.today_str}, Dates: {from_date}, {to_date}")
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
        print(f"DEBUG: Processing query for ID {query_id}: {sql_query[:100]}...")
        from_date, to_date = self.date_extractor.extract_dates(sql_query, ast)
        print(f"DEBUG: Extracted dates for query ID {query_id}: {from_date}, {to_date}")
        
        # 날짜 정보 저장
        self.date_ranges[query_id] = (from_date, to_date)
        
        # 미래 날짜 처리
        if from_date > self.date_extractor.today_str or to_date > self.date_extractor.today_str:
            print(f"DEBUG: Future date in query {query_id}. Today: {self.date_extractor.today_str}, Dates: {from_date}, {to_date}")
            self.flags["future_date"] = True
            # 미래 날짜를 현재 날짜로 조정
            if from_date > self.date_extractor.today_str:
                from_date = self.date_extractor.today_str
            if to_date > self.date_extractor.today_str:
                to_date = self.date_extractor.today_str
            self.date_ranges[query_id] = (from_date, to_date)
            print(f"DEBUG: Adjusted dates for query ID {query_id}: {from_date}, {to_date}")

        def transform_table(node: exp.Expression) -> exp.Expression:
            """테이블 참조를 뷰 함수 호출로 변환"""
            if isinstance(node, exp.Table):
                # aicfo_get_all_* 테이블 변환
                if node.name.startswith('aicfo_get_all_'):
                    # 해당 쿼리 ID의 날짜 정보 사용
                    from_date, to_date = self.date_ranges.get(query_id, ("", ""))
                    print(f"DEBUG: Creating view function for table {node.name} with dates: {from_date}, {to_date}")
                    
                    # 뷰 함수 생성
                    view_func = self._create_view_function(
                        ViewFunction(
                            base_name=node.name,
                            use_intt_id=self.use_intt_id,
                            user_id=self.user_id,
                            view_com=self.view_com,
                            from_date=from_date,
                            to_date=to_date,
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
            print(f"DEBUG: Query {query_id} has subqueries, processing them")
            transformed_ast = self._handle_subqueries(transformed_ast)
        
        return transformed_ast

    def _handle_subqueries(self, ast: exp.Expression) -> exp.Expression:
        """AST 내의 서브쿼리 처리"""
        def transform_subquery(node: exp.Expression) -> exp.Expression:
            """서브쿼리 노드 변환"""
            if isinstance(node, exp.Subquery):
                # 서브쿼리에 고유 ID 부여
                self.query_counter += 1
                subquery_id = f"subquery_{self.query_counter}"
                
                # 서브쿼리 SQL 추출
                subquery_sql = node.this.sql(dialect='postgres')
                print(f"DEBUG: Processing subquery with ID: {subquery_id}, SQL: {subquery_sql[:100]}...")
                
                # 서브쿼리만의 날짜 조건 추출
                conditions = self.date_extractor._extract_date_conditions(node.this)
                print(f"DEBUG: Extracted conditions for subquery {subquery_id}: {conditions}")
                
                # 서브쿼리에서 날짜 조건이 있는지 확인
                has_date_condition = any(
                    condition.column in ['reg_dt', 'trsc_dt'] 
                    for condition in conditions
                )
                
                if has_date_condition:
                    # 서브쿼리 자체 날짜 조건이 있는 경우
                    from_date = self.date_extractor.today_str
                    to_date = self.date_extractor.today_str
                    
                    # 특별히 trsc_dt > 'YYYYMMDD' 형태의 조건 처리
                    for condition in conditions:
                        if condition.column == 'trsc_dt' and condition.operator in ('GT', '>'):
                            value = str(condition.value).strip("'")
                            # 날짜 형식 정규화
                            if len(value) != 8:
                                value = value.replace("-", "")
                            # 다음 날짜 계산 (GT는 초과이므로 +1일)
                            from_date = self.date_extractor._add_days(value, 1)
                            break
                    
                    # 날짜 범위 저장 - 서브쿼리의 고유 날짜 설정
                    self.date_ranges[subquery_id] = (from_date, to_date)
                    print(f"DEBUG: Set subquery date range from its own conditions: {from_date} to {to_date}")
                else:
                    # 서브쿼리에 날짜 조건이 없는 경우, 부모 쿼리의 날짜 범위 사용
                    parent_query_id = "main"  # 기본값, 실제로는 부모 쿼리 ID를 전달받아야 함
                    parent_from_date, parent_to_date = self.date_ranges.get(parent_query_id, 
                        (self.date_extractor.today_str, self.date_extractor.today_str))
                    
                    self.date_ranges[subquery_id] = (parent_from_date, parent_to_date)
                    print(f"DEBUG: Using parent query date range for subquery: {parent_from_date} to {parent_to_date}")
                
                # 미래 날짜 처리
                if from_date > self.date_extractor.today_str:
                    print(f"DEBUG: Future date in subquery. Today: {self.date_extractor.today_str}, from_date: {from_date}")
                    self.flags["future_date"] = True
                    from_date = self.date_extractor.today_str
                    self.date_ranges[subquery_id] = (from_date, to_date)
                
                # 최종 날짜 값 캡처
                subquery_from_date, subquery_to_date = self.date_ranges[subquery_id]
                
                # 서브쿼리 내의 테이블 참조 변환
                def transform_table_only(n: exp.Expression) -> exp.Expression:
                    if isinstance(n, exp.Table):
                        if n.name.startswith('aicfo_get_all_'):
                            view_func = self._create_view_function(
                                ViewFunction(
                                    base_name=n.name,
                                    use_intt_id=self.use_intt_id,
                                    user_id=self.user_id,
                                    view_com=self.view_com,
                                    from_date=subquery_from_date,
                                    to_date=subquery_to_date,
                                    alias=n.alias,
                                    query_id=subquery_id
                                )
                            )
                            return view_func
                    return n
                
                # 테이블 참조 변환한 서브쿼리 생성
                transformed_subquery = node.this.transform(transform_table_only)
                
                return exp.Subquery(this=transformed_subquery)
                    
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
        # 함수 호출 표현식 생성
        func_call = exp.Anonymous(
            this=view_func.base_name,
            expressions=[
                # 함수 매개변수: use_intt_id, user_id, view_com, from_date, to_date
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
        Args:
            query: SQL 쿼리 문자열
        Returns:
            bool: 변환 가능 여부
        """
        try:
            sqlglot.parse_one(query, dialect='postgres')
            return True
        except ParseError:
            return False