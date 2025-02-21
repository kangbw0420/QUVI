from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Set
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

@dataclass
class DateRange:
    """날짜 범위 정보"""
    from_date: str
    to_date: str
    source_column: str  # reg_dt or trsc_dt
    is_between: bool = False
    is_single_date: bool = False

@dataclass
class DateCondition:
    """SQL의 날짜 조건절 정보"""
    column: str
    operator: str  # =, >, <, >=, <=, BETWEEN
    value: str
    secondary_value: Optional[str] = None  # BETWEEN의 두 번째 값

class DateExtractor:
    def __init__(self, selected_table: str, today: str):
        """
        Args:
            selected_table: 'amt', 'stock', 또는 'trsc'
            today: 'YYYY-MM-DD' 형식의 오늘 날짜
        """
        self.selected_table = selected_table
        self.date_column = 'reg_dt' if selected_table in ['amt', 'stock'] else 'trsc_dt'
        self.today = datetime.strptime(today, "%Y-%m-%d")
        self.today_str = self.today.strftime("%Y%m%d")
        self.flags = {
            'future_date': False,
            'past_date': False
        }

    def extract_dates(self, query: str) -> Tuple[str, str]:
        """쿼리에서 날짜 범위를 추출하고 검증"""
        try:
            # 쿼리 파싱
            ast = sqlglot.parse_one(query, dialect='postgres')
            
            # 날짜 조건 추출
            date_conditions = self._extract_date_conditions(ast)
            
            # due_dt 조건 추출 및 처리
            due_date_conditions = self._extract_due_date_conditions(ast)
            
            # 날짜 범위 결정
            date_range = self._determine_date_range(date_conditions, due_date_conditions)
            
            return date_range.from_date, date_range.to_date
            
        except ParseError:
            # 파싱 실패시 오늘 날짜 반환
            return self.today_str, self.today_str

    def _extract_date_conditions(self, ast: exp.Expression) -> List[DateCondition]:
        """AST에서 날짜 조건 추출"""
        conditions = []
        
        def extract_from_node(node: exp.Expression):
            # BETWEEN 조건 처리
            if (isinstance(node, exp.Between) and
                isinstance(node.this, exp.Column) and
                node.this.name == self.date_column):
                conditions.append(DateCondition(
                    column=self.date_column,
                    operator='BETWEEN',
                    value=node.args["low"].this,
                    secondary_value=node.args['high'].this
                ))

            # 비교 연산자 조건 처리
            elif isinstance(node, (exp.EQ, exp.GT, exp.LT, exp.GTE, exp.LTE)):
                if (isinstance(node.this, exp.Column) and 
                    node.this.name == self.date_column):
                    conditions.append(DateCondition(
                        column=self.date_column,
                        operator=node.__class__.__name__,  # op 대신 클래스 이름
                        value=node.expression.this
                    ))

        # AST 순회하며 조건 수집
        for node in ast.walk():
            extract_from_node(node)
            
        return conditions

    def _extract_due_date_conditions(self, ast: exp.Expression) -> List[DateCondition]:
        """AST에서 due_dt 조건 추출"""
        conditions = []
        
        def extract_from_node(node: exp.Expression):
            if (isinstance(node, exp.Between) and
                isinstance(node.this, exp.Column) and
                node.this.name == 'due_dt'):
                conditions.append(DateCondition(
                    column='due_dt',
                    operator='BETWEEN',
                    value=node.args['low'].this,
                    secondary_value=node.args['high'].this
                ))

            # 비교 연산자 조건 처리
            elif isinstance(node, (exp.EQ, exp.GT, exp.LT, exp.GTE, exp.LTE)):
                if (isinstance(node.this, exp.Column) and 
                    node.this.name == 'due_dt'):
                    conditions.append(DateCondition(
                        column='due_dt',
                        operator=node.__class__.__name__,  # op 대신 클래스 이름
                        value=node.expression.this
                    ))

        for node in ast.walk():
            extract_from_node(node)
            
        return conditions

    def _determine_date_range(self, 
                            date_conditions: List[DateCondition],
                            due_date_conditions: List[DateCondition]) -> DateRange:
        """날짜 조건들로부터 최종 날짜 범위 결정"""
        
        def normalize_date(date_str: str) -> str:
            """날짜 문자열을 YYYYMMDD 형식으로 정규화"""
            date_str = date_str.strip("'")
            return date_str if len(date_str) == 8 else date_str.replace("-", "")

        def validate_future_date(date_str: str) -> str:
            """미래 날짜를 오늘 날짜로 조정"""
            date_str = normalize_date(date_str)
            if date_str > self.today_str:
                self.flags['future_date'] = True
                return self.today_str
            return date_str

        # 조건이 없는 경우 오늘 날짜 반환
        if not date_conditions and not due_date_conditions:
            return DateRange(self.today_str, self.today_str, self.date_column)

        dates = []
        
        # 일반 날짜 조건 처리
        for condition in date_conditions:
            if condition.operator == 'BETWEEN':
                dates.append(validate_future_date(condition.value))
                dates.append(validate_future_date(condition.secondary_value))
            else:
                dates.append(validate_future_date(condition.value))

        # due_dt 조건 처리
        due_dates = []
        for condition in due_date_conditions:
            if condition.operator == 'BETWEEN':
                due_dates.extend([
                    normalize_date(condition.value),
                    normalize_date(condition.secondary_value)
                ])
            else:
                due_dates.append(normalize_date(condition.value))

        # 날짜 범위 결정
        if dates:
            from_date = min(dates)
            to_date = min(max(dates), self.today_str)
        else:
            from_date = to_date = self.today_str

        # due_dt 제약 적용
        if due_dates:
            due_from = min(due_dates)
            due_to = max(due_dates)
            # due_dt 범위가 더 제한적인 경우 적용
            if due_to < to_date:
                from_date = due_from
                to_date = due_to

        return DateRange(
            from_date=from_date,
            to_date=to_date,
            source_column=self.date_column,
            is_between=len(dates) > 1 or len(due_dates) > 1,
            is_single_date=from_date == to_date
        )

    def check_past_date_access(self, from_date: str) -> bool:
        """무료 계정의 과거 데이터 접근 제한 체크"""
        from_dt = datetime.strptime(from_date, "%Y%m%d")
        date_diff = self.today - from_dt
        
        if date_diff.days >= 2:
            self.flags['past_date'] = True
            return True
        return False

# Usage example
def extract_view_date(query: str, selected_table: str, flags: dict) -> Tuple[str, str]:
    """기존 인터페이스와 호환되는 래퍼 함수"""
    today = datetime.now().strftime("%Y-%m-%d")
    extractor = DateExtractor(selected_table, today)
    
    from_date, to_date = extractor.extract_dates(query)
    
    # Update flags
    flags.update(extractor.flags)
    
    return from_date, to_date