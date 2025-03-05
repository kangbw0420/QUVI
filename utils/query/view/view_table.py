import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError
from datetime import datetime, timedelta

from utils.query.view.classify_query import QueryClassifier
from utils.query.view.extract_date import DateExtractor, DateCondition

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
        
    def _handle_node_recursively(self, node: exp.Expression, node_id: str) -> exp.Expression:
        """모든 타입의 노드를 재귀적으로 처리"""        
        # Union 노드 처리
        if isinstance(node, exp.Union):
            # 왼쪽과 오른쪽 부분에 대해 재귀적으로 처리
            left_id = f"{node_id}_left"
            right_id = f"{node_id}_right"
            
            transformed_left = self._handle_node_recursively(node.left, left_id)
            transformed_right = self._handle_node_recursively(node.right, right_id)
            
            distinct_value = node.args.get('distinct', False)
            # 변환된 UNION 생성
            transformed_node = exp.Union(
                this=transformed_left,
                expression=transformed_right,
                distinct=distinct_value
            )
            
            # 부모 노드의 날짜 범위는 양쪽 자식의 병합된 범위
            if left_id in self.date_ranges and right_id in self.date_ranges:
                left_from, left_to = self.date_ranges[left_id]
                right_from, right_to = self.date_ranges[right_id]
                
                merged_from = min(left_from, right_from)
                merged_to = max(left_to, right_to)
                
                self.date_ranges[node_id] = (merged_from, merged_to)
                
                # 미래 날짜 확인
                if merged_from > self.date_extractor.today_str or merged_to > self.date_extractor.today_str:
                    self.flags["future_date"] = True
            
            return transformed_node
        
        # Select 노드 처리
        elif isinstance(node, exp.Select):
            # 노드 복사 - 변경 사항을 적용할 새로운 Select 객체
            transformed_node = node
            
            # 먼저 노드에서 직접 날짜 조건 추출 (WHERE 절에서)
            if node.args.get("where"):
                where_node = node.args["where"]
                # WHERE 절에서 날짜 조건 직접 추출
                date_conditions = self._extract_date_conditions_direct(where_node)
                
                if date_conditions:
                    # 추출된 날짜 조건이 있으면 날짜 범위 결정
                    from_date = None
                    to_date = None
                    
                    for condition in date_conditions:
                        if condition.column in ['reg_dt', 'trsc_dt']:
                            if condition.operator == 'BETWEEN':
                                # BETWEEN에서는 범위 직접 사용
                                cond_from = condition.value
                                cond_to = condition.secondary_value
                                from_date = cond_from if from_date is None else min(from_date, cond_from)
                                to_date = cond_to if to_date is None else max(to_date, cond_to)
                            elif condition.operator in ('EQ', '='):
                                # 등호에서는 같은 날짜
                                cond_date = condition.value
                                from_date = cond_date if from_date is None else min(from_date, cond_date)
                                to_date = cond_date if to_date is None else max(to_date, cond_date)
                            # 다른 연산자에 대한 처리 추가 가능
                    
                    if from_date and to_date:
                        self.date_ranges[node_id] = (from_date, to_date)
                        
                        # 미래 날짜 처리
                        if from_date > self.date_extractor.today_str or to_date > self.date_extractor.today_str:
                            self.flags["future_date"] = True
            
            # FROM 절 처리 (서브쿼리 포함)
            if node.args.get("from"):
                from_clause = node.args["from"]
                
                # FROM 절이 From 객체인 경우
                if isinstance(from_clause, exp.From):
                    if isinstance(from_clause.this, exp.Subquery):
                        # 서브쿼리에 고유 ID 할당
                        subquery_id = f"{node_id}_sub"
                        
                        # 서브쿼리 내부를 재귀적으로 처리
                        transformed_subquery = self._handle_node_recursively(from_clause.this.this, subquery_id)
                        
                        # 변환된 서브쿼리로 FROM 절 업데이트
                        new_from = exp.From(
                            this=exp.Subquery(
                                this=transformed_subquery
                            )
                        )
                        transformed_node.args["from"] = new_from
                        
                        # 날짜 범위 상속
                        if subquery_id in self.date_ranges:
                            sub_from, sub_to = self.date_ranges[subquery_id]
                            if node_id in self.date_ranges:
                                node_from, node_to = self.date_ranges[node_id]
                                self.date_ranges[node_id] = (
                                    min(node_from, sub_from),
                                    max(node_to, sub_to)
                                )
                            else:
                                self.date_ranges[node_id] = (sub_from, sub_to)
                    elif isinstance(from_clause.this, exp.Table):
                        # 테이블 참조 변환
                        if from_clause.this.name.startswith('aicfo_get_all_'):
                            # 현재 노드의 날짜 범위 가져오기
                            if node_id in self.date_ranges:
                                current_from_date, current_to_date = self.date_ranges[node_id]
                            else:
                                # 날짜 범위가 없으면 SQL에서 추출 시도
                                try:
                                    sql_query = node.sql(dialect='postgres')
                                    current_from_date, current_to_date = self.date_extractor.extract_dates(sql_query)
                                    self.date_ranges[node_id] = (current_from_date, current_to_date)
                                except:
                                    current_from_date = current_to_date = self.date_extractor.today_str
                            
                            view_func = self._create_view_function(
                                ViewFunction(
                                    base_name=from_clause.this.name,
                                    use_intt_id=self.use_intt_id,
                                    user_id=self.user_id,
                                    view_com=self.view_com,
                                    from_date=current_from_date,
                                    to_date=current_to_date,
                                    alias=from_clause.this.alias,
                                    query_id=node_id
                                )
                            )
                            transformed_node.args["from"] = exp.From(this=view_func)
            
            # WHERE 절 내 IN 조건의 서브쿼리 처리
            if transformed_node.args.get("where"):
                def process_where_subqueries(expr, parent_id):
                    if isinstance(expr, exp.In) and isinstance(expr.expression, exp.Subquery):
                        # IN 조건의 서브쿼리 처리
                        subquery_id = f"{parent_id}_in_sub"
                        transformed_subquery = self._handle_node_recursively(expr.expression.this, subquery_id)
                        
                        # 변환된 서브쿼리로 IN 조건 업데이트
                        return exp.In(
                            this=expr.this,
                            expression=exp.Subquery(this=transformed_subquery),
                            invert=expr.args.get("invert", False)
                        )
                    
                    # 그 외 AND/OR 조건 처리
                    elif isinstance(expr, (exp.And, exp.Or)):
                        new_this = process_where_subqueries(expr.this, f"{parent_id}_this")
                        new_expression = process_where_subqueries(expr.expression, f"{parent_id}_expr")
                        
                        if isinstance(expr, exp.And):
                            return exp.And(this=new_this, expression=new_expression)
                        else:  # Or
                            return exp.Or(this=new_this, expression=new_expression)
                    
                    return expr
                
                # WHERE 절 서브쿼리 처리
                transformed_node.args["where"] = process_where_subqueries(transformed_node.args["where"], f"{node_id}_where")
            
            # 최종 변환된 노드 반환
            return transformed_node
        
        # Subquery 노드 처리
        elif isinstance(node, exp.Subquery):
            subquery_id = f"{node_id}_inner"
            
            # 내부 쿼리를 재귀적으로 처리
            transformed_inner = self._handle_node_recursively(node.this, subquery_id)
            
            # 변환된 서브쿼리 생성
            transformed_node = exp.Subquery(this=transformed_inner)
            
            # 날짜 범위 상속
            if subquery_id in self.date_ranges:
                self.date_ranges[node_id] = self.date_ranges[subquery_id]
            
            return transformed_node
        
        # 일반 노드 처리
        else:
            try:
                # 현재 노드가 Table이면서 aicfo_get_all_*인 경우 뷰 함수로 변환
                if isinstance(node, exp.Table) and node.name.startswith('aicfo_get_all_'):
                    # 현재 노드에 대한 날짜 정보 가져오기
                    if node_id not in self.date_ranges:
                        # 부모 노드에서 날짜 정보 상속
                        parent_id = node_id.rsplit('_', 1)[0] if '_' in node_id else "main"
                        if parent_id in self.date_ranges:
                            self.date_ranges[node_id] = self.date_ranges[parent_id]
                        else:
                            self.date_ranges[node_id] = (self.date_extractor.today_str, self.date_extractor.today_str)
                    
                    current_from_date, current_to_date = self.date_ranges[node_id]
                    
                    # 뷰 함수 생성
                    view_func = self._create_view_function(
                        ViewFunction(
                            base_name=node.name,
                            use_intt_id=self.use_intt_id,
                            user_id=self.user_id,
                            view_com=self.view_com,
                            from_date=current_from_date,
                            to_date=current_to_date,
                            alias=node.alias,
                            query_id=node_id
                        )
                    )
                    
                    return view_func
                
                # 그 외 일반 노드는 그대로 반환
                return node
                    
            except Exception as e:
                print(f"Error processing node {node_id}: {str(e)}")
                return node

    def _extract_date_conditions_direct(self, node: exp.Expression) -> list:
        """AST 노드에서 직접 날짜 조건 추출"""
        conditions = []
        date_pattern = re.compile(r"\d{8}|\d{4}-\d{2}-\d{2}")
        
        # Between 조건 확인
        if isinstance(node, exp.Between):
            if (isinstance(node.this, exp.Column) and 
                (node.this.name == 'reg_dt' or node.this.name == 'trsc_dt')):
                low_value = str(node.args["low"].this).strip("'")
                high_value = str(node.args["high"].this).strip("'")

                if date_pattern.match(low_value) and date_pattern.match(high_value):
                    conditions.append(DateCondition(
                        column=node.this.name,
                        operator='BETWEEN',
                        value=low_value,
                        secondary_value=high_value
                    ))
        
        # 등호 조건 확인
        elif isinstance(node, (exp.EQ, exp.GT, exp.LT, exp.GTE, exp.LTE)):
            if (isinstance(node.this, exp.Column) and 
                (node.this.name == 'reg_dt' or node.this.name == 'trsc_dt')):
                value = str(node.expression.this).strip("'")
                op_name = node.__class__.__name__
                
                if date_pattern.match(value):
                    conditions.append(DateCondition(
                        column=node.this.name,
                        operator=op_name,
                        value=value
                    ))
        
        # AND 조건 처리
        elif isinstance(node, exp.And):
            # 양쪽 하위 노드에서 조건 추출
            left_conditions = self._extract_date_conditions_direct(node.this)
            right_conditions = self._extract_date_conditions_direct(node.expression)
            conditions.extend(left_conditions)
            conditions.extend(right_conditions)
        
        # OR 조건 처리
        elif isinstance(node, exp.Or):
            # 양쪽 하위 노드에서 조건 추출
            left_conditions = self._extract_date_conditions_direct(node.this)
            right_conditions = self._extract_date_conditions_direct(node.expression)
            conditions.extend(left_conditions)
            conditions.extend(right_conditions)
        
        return conditions

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
            
            ast = sqlglot.parse_one(query, dialect='postgres')
            transformed_ast = self._handle_node_recursively(ast, "main")
                
            # 변환된 SQL 문자열
            transformed_sql = transformed_ast.sql(dialect='postgres')
            
            # date_ranges가 비어있으면 기본값 추가
            if 'main' not in self.date_ranges:
                today = self.date_extractor.today_str
                self.date_ranges['main'] = (today, today)
            
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

def view_table(query_ordered: str, selected_table: str, 
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
    transformed_query, date_ranges = transformer.transform_query(query_ordered)

    return transformed_query, date_ranges