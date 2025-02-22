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
        print(f"DEBUG: DateExtractor!!!!! with date_column={self.date_column}, today={self.today_str}")

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
                print("특정 노드 범위 있음")
                date_conditions = self._extract_date_conditions(node_scope)
                due_date_conditions = self._extract_due_date_conditions(node_scope)
            else:
                # 전체 쿼리에서 날짜 조건 추출
                print("특정 노드 범위 없음. 전체 쿼리 사용")
                date_conditions = self._extract_date_conditions(ast)
                due_date_conditions = self._extract_due_date_conditions(ast)
            
            print(f"DEBUG: 날짜 찾음: {date_conditions}")
            print(f"DEBUG: due date가 있는가?: {due_date_conditions}")
            
            date_range = self._determine_date_range(date_conditions, due_date_conditions)
            print(f"DEBUG: 날짜 범위 결정: {date_range}")
            
            return date_range.from_date, date_range.to_date
            
        except Exception as e:
            print(f"DEBUG: Error in extract_dates: {e}")
            return self.today_str, self.today_str

    def _extract_date_conditions(self, ast: exp.Expression) -> List[DateCondition]:
        """AST에서 날짜 조건 추출"""
        conditions = []
        date_pattern = re.compile(r"\d{8}|\d{4}-\d{2}-\d{2}")
        
        def extract_from_node(node: exp.Expression):
            if isinstance(node, exp.Between):
                if (isinstance(node.this, exp.Column) and 
                    (node.this.name == 'reg_dt' or node.this.name == 'trsc_dt')):
                    low_value = str(node.args["low"].this).strip("'")
                    high_value = str(node.args["high"].this).strip("'")
                    
                    print(f"DEBUG: Found BETWEEN condition on {node.this.name}: {low_value} AND {high_value}")
                    
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
                    
                    print(f"DEBUG: Found {op_name} condition on {node.this.name}: {value}")
                    
                    if date_pattern.match(value):
                        conditions.append(DateCondition(
                            column=node.this.name,
                            operator=op_name,
                            value=value
                        ))
        
        for node in ast.walk():
            extract_from_node(node)
            
        return conditions

    def _extract_due_date_conditions(self, ast: exp.Expression) -> List[DateCondition]:
        conditions = []
        date_pattern = re.compile(r"\d{8}|\d{4}-\d{2}-\d{2}")
        
        def extract_from_node(node: exp.Expression):
            if isinstance(node, exp.Between):
                if (isinstance(node.this, exp.Column) and node.this.name == 'due_dt'):
                    low_value = str(node.args["low"].this).strip("'")
                    high_value = str(node.args["high"].this).strip("'")
                    
                    print(f"DEBUG: Found BETWEEN condition on due_dt: {low_value} AND {high_value}")
                    
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
                    
                    print(f"DEBUG: Found {op_name} condition on due_dt: {value}")
                    
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
        """날짜 조건들로부터 최종 날짜 범위 결정"""
        
        def normalize_date(date_str: str) -> str:
            """날짜 문자열을 YYYYMMDD 형식으로 정규화"""
            date_str = str(date_str).strip("'")
            return date_str if len(date_str) == 8 else date_str.replace("-", "")

        # 조건이 없는 경우 오늘 날짜 반환
        if not date_conditions and not due_date_conditions:
            return DateRange(self.today_str, self.today_str, self.date_column)

        # 컬럼별 범위 추적
        date_ranges = {}
        
        # 컬럼 및 연산자별 조건 처리
        for condition in date_conditions:
            col = condition.column
            if col not in date_ranges:
                date_ranges[col] = {
                    'min_date': "99991231",  # 초기값: 먼 미래
                    'max_date': "19700101"   # 초기값: 먼 과거
                }
                
            value = normalize_date(condition.value)
            
            if condition.operator == 'BETWEEN':
                second_value = normalize_date(condition.secondary_value)
                date_ranges[col]['min_date'] = min(date_ranges[col]['min_date'], value)
                date_ranges[col]['max_date'] = max(date_ranges[col]['max_date'], second_value)
                
            elif condition.operator in ('EQ', '='):
                # 동일한 날짜
                date_ranges[col]['min_date'] = min(date_ranges[col]['min_date'], value)
                date_ranges[col]['max_date'] = max(date_ranges[col]['max_date'], value)
                
            elif condition.operator in ('GT', '>'):
                # 다음 날짜부터
                next_day = self._add_days(value, 1)
                date_ranges[col]['min_date'] = min(date_ranges[col]['min_date'], next_day)
                
            elif condition.operator in ('GTE', '>='):
                # 해당 날짜부터
                date_ranges[col]['min_date'] = min(date_ranges[col]['min_date'], value)
                
            elif condition.operator in ('LT', '<'):
                # 전날까지
                prev_day = self._add_days(value, -1)
                date_ranges[col]['max_date'] = max(date_ranges[col]['max_date'], prev_day)
                
            elif condition.operator in ('LTE', '<='):
                # 해당 날짜까지
                date_ranges[col]['max_date'] = max(date_ranges[col]['max_date'], value)
        
        # 모든 컬럼의 날짜 범위 확인 및 결합
        all_min_dates = []
        all_max_dates = []
        
        for col, range_data in date_ranges.items():
            # 범위가 유효한지 확인 (min <= max)
            if range_data['min_date'] <= range_data['max_date']:
                all_min_dates.append((range_data['min_date'], col))
                all_max_dates.append((range_data['max_date'], col))

        # 최종 날짜 범위 및 소스 컬럼 선택
        if all_min_dates:
            # 가장 늦은 시작 날짜와 가장 빠른 종료 날짜를 사용
            # (가장 제한적인 범위)
            all_min_dates.sort()  # 날짜 오름차순 정렬
            all_max_dates.sort(reverse=True)  # 날짜 내림차순 정렬
            
            from_date, from_col = all_min_dates[-1]  # 가장 늦은 시작 날짜
            to_date, to_col = all_max_dates[-1]  # 가장 빠른 종료 날짜
            
            # 범위 확인: 시작 날짜가 종료 날짜보다 늦으면 단일 날짜 사용
            if from_date > to_date:
                from_date = to_date = self.today_str
                source_column = self.date_column
            else:
                # 더 많은 조건이 있는 컬럼을 소스로 선택
                from_col_count = sum(1 for c in date_conditions if c.column == from_col)
                to_col_count = sum(1 for c in date_conditions if c.column == to_col)
                
                source_column = from_col if from_col_count >= to_col_count else to_col
        else:
            from_date = to_date = self.today_str
            source_column = self.date_column
        
        print(f"DEBUG: Final date range determined: {from_date} to {to_date}")
        
        return DateRange(
            from_date=from_date,
            to_date=to_date,
            source_column=source_column,
            is_between=len(date_ranges) > 0,
            is_single_date=from_date == to_date
        )

    def _add_days(self, date_str: str, days: int) -> str:
        """날짜 문자열에 일수를 더하거나 뺌"""
        try:
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            new_date = date_obj + timedelta(days=days)
            return new_date.strftime("%Y%m%d")
        except Exception as e:
            print(f"DEBUG: Error adding days to date: {e}")
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