from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Set, Dict, Any
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError
import re

@dataclass
class DateRange:
    from_date: str
    to_date: str
    source_column: str  # reg_dt or trsc_dt
    is_between: bool = False
    is_single_date: bool = False

@dataclass
class DateCondition:
    column: str
    operator: str  # =, >, <, >=, <=, BETWEEN
    value: str
    secondary_value: Optional[str] = None  # BETWEEN의 두 번째 값

class DateExtractor:
    def __init__(self, selected_table: str = None):
        self.selected_table = selected_table
        self.date_column = 'reg_dt' if selected_table in ['amt', 'stock'] else 'trsc_dt'
        self.today = datetime.now()
        self.today_str = self.today.strftime("%Y%m%d")

    def extract_dates(self, query: str, node_scope=None) -> Tuple[str, str]:
        """쿼리에서 날짜 범위를 추출하고 검증, node_scope 매개변수 추가
        Args:
            query: SQL 쿼리 문자열
            node_scope: 특정 AST 노드 내에서만 조건을 추출하기 위한 범위 제한
        Returns:
            Tuple[str, str]: (from_date, to_date) 형식의 날짜 범위
        """
        try:
            ast = sqlglot.parse_one(query, dialect='postgres')
            
            # 특정 노드 범위가 지정된 경우 해당 노드만 사용
            if node_scope:
                date_conditions = self._extract_date_conditions(node_scope)
                due_date_conditions = self._extract_due_date_conditions(node_scope)
            else:
                # 전체 쿼리에서 날짜 조건 추출
                date_conditions = self._extract_date_conditions(ast)
                due_date_conditions = self._extract_due_date_conditions(ast)
            
            date_range = self._determine_date_range(date_conditions, due_date_conditions)
            
            return date_range.from_date, date_range.to_date
            
        except Exception as e:
            print(f"Error in extract_dates: {e}")
            # 예외 발생 시 기본값 반환
            return self.today_str, self.today_str

    def _extract_date_conditions(self, ast: exp.Expression) -> List[DateCondition]:
        """AST에서 날짜 조건 추출"""
        conditions = []
        date_pattern = re.compile(r"\d{8}|\d{4}-\d{2}-\d{2}")
        visited_nodes = set()
        
        def extract_from_node(node: exp.Expression):
            # 이미 방문한 노드는 건너뛰기
            node_id = id(node)
            if node_id in visited_nodes:
                return
            visited_nodes.add(node_id)
            
            # 서브쿼리는 건너뛰기 - 중요!
            if isinstance(node, exp.Subquery):
                return

            # extract date condition
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
        
            # 자식 노드 처리
            for arg_name, arg_value in node.args.items():
                if isinstance(arg_value, exp.Expression):
                    extract_from_node(arg_value)
                elif isinstance(arg_value, list):
                    for item in arg_value:
                        if isinstance(item, exp.Expression):
                            extract_from_node(item)
        
        # 루트 노드부터 처리 시작
        extract_from_node(ast)
        return conditions

    def _extract_due_date_conditions(self, ast: exp.Expression) -> List[DateCondition]:
        conditions = []
        date_pattern = re.compile(r"\d{8}|\d{4}-\d{2}-\d{2}")
        
        def extract_from_node(node: exp.Expression):
            if isinstance(node, exp.Between):
                if (isinstance(node.this, exp.Column) and node.this.name == 'due_dt'):
                    low_value = str(node.args["low"].this).strip("'")
                    high_value = str(node.args["high"].this).strip("'")
                    
                    if date_pattern.match(low_value) and date_pattern.match(high_value):
                        conditions.append(DateCondition(
                            column='due_dt',
                            operator='BETWEEN',
                            value=low_value,
                            secondary_value=high_value
                        ))
            elif isinstance(node, (exp.EQ, exp.GT, exp.LT, exp.GTE, exp.LTE)):
                if (isinstance(node.this, exp.Column) and node.this.name == 'due_dt'):
                    value = str(node.expression.this).strip("'")
                    op_name = node.__class__.__name__
                    
                    if date_pattern.match(value):
                        conditions.append(DateCondition(
                            column='due_dt',
                            operator=op_name,
                            value=value
                        ))

        for node in ast.walk():
            extract_from_node(node)
            
        return conditions

    def _determine_date_range(self, date_conditions: List[DateCondition], due_date_conditions: List[DateCondition]) -> DateRange:
        """여러 날짜 조건을 고려하여 날짜 범위 결정"""
        
        # 조건이 없는 경우 오늘 날짜
        if not date_conditions and not due_date_conditions:
            return DateRange(self.today_str, self.today_str, self.date_column)

        # 초기 날짜 범위 설정
        from_date = "19700101"  # 가장 과거
        to_date = self.today_str  # 현재 날짜
        source_column = self.date_column
        is_between = False
        is_single_date = False
        
        # 등호 조건을 별도로 저장 (바로 반환하지 않음)
        eq_condition = None
        
        # 일반 날짜 조건(reg_dt, trsc_dt)을 처리
        for condition in date_conditions:
            if condition.operator in ('EQ', '='):
                # 등호 조건 저장
                eq_condition = condition
                from_date = condition.value
                to_date = condition.value
                source_column = condition.column
                is_single_date = True
            elif condition.operator == 'BETWEEN':
                # BETWEEN 조건은 독립적인 범위로 취급
                from_date = condition.value
                to_date = condition.secondary_value
                source_column = condition.column
                is_between = True
            elif condition.operator in ('GT', '>'):
                # 다음 날부터 시작하는 조건
                next_day = self._add_days(condition.value, 1)
                if next_day > from_date:
                    from_date = next_day
                    source_column = condition.column
            elif condition.operator in ('GTE', '>='):
                if condition.value > from_date:
                    from_date = condition.value
                    source_column = condition.column
            elif condition.operator in ('LT', '<'):
                prev_day = self._add_days(condition.value, -1)
                if prev_day < to_date:
                    to_date = prev_day
                    source_column = condition.column
            elif condition.operator in ('LTE', '<='):
                if condition.value < to_date:
                    to_date = condition.value
                    source_column = condition.column
        
        # due_dt 조건 처리
        due_from_date = "99991231"  # 가장 먼 미래
        
        for condition in due_date_conditions:
            if condition.operator in ('EQ', '='):
                # 만기일이 특정 날짜인 경우
                due_from_date = condition.value
            elif condition.operator == 'BETWEEN':
                # 만기일이 범위인 경우
                due_from_date = condition.value
            elif condition.operator in ('GT', '>'):
                # 만기일이 특정 날짜 이후인 경우
                due_from_date = self._add_days(condition.value, 1)
            elif condition.operator in ('GTE', '>='):
                # 만기일이 특정 날짜 이상인 경우
                due_from_date = condition.value
        
        # 날짜 조건이 없고 만기일 조건만 있는 경우
        if not date_conditions and due_date_conditions:
            if due_from_date != "99991231":
                from_date = due_from_date
        # 날짜 조건과 만기일 조건이 모두 있는 경우
        elif date_conditions and due_date_conditions:
            # due_from_date가 일반 from_date보다 앞에 있으면 from_date를 조정
            if due_from_date != "99991231" and due_from_date < from_date:
                # 등호 조건이 있어도 due_dt가 더 이전이면 from_date를 조정
                from_date = due_from_date
                is_single_date = False  # 단일 날짜 조건 해제
        
        return DateRange(from_date, to_date, source_column, is_between, is_single_date)

    def _add_days(self, date_str: str, days: int) -> str:
        """날짜 문자열에 일수를 더하거나 뺌"""
        try:
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            new_date = date_obj + timedelta(days=days)
            return new_date.strftime("%Y%m%d")
        except Exception as e:
            print(f"Error adding days to date: {e}")
            return date_str

    @staticmethod
    def is_future_date(date_str: str) -> bool:
        """날짜가 미래인지 확인"""
        try:
            today = datetime.now().strftime("%Y%m%d")
            return date_str > today
        except:
            return False

    def check_past_date_access(self, from_date: str, to_date: str) -> bool:
        """무료 계정의 과거 데이터 접근 제한 체크"""
        try:
            from_dt = datetime.strptime(from_date, "%Y%m%d")
            date_diff = self.today - from_dt
            
            if date_diff.days >= 2:
                return True
            return False
        except:
            return False