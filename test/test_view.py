import pytest
from datetime import datetime, timedelta
import sqlglot
from sqlglot import exp

from utils.query.view.extract_date import DateExtractor, DateCondition, DateRange


class TestDateExtractor:
    
    def setup_method(self):
        self.extractor = DateExtractor(selected_table="amt")  # amt 테이블에서는 reg_dt가 기본 날짜 컬럼
        self.extractor_trsc = DateExtractor(selected_table="trsc")  # trsc 테이블에서는 trsc_dt가 기본 날짜 컬럼
        
        # 오늘 날짜와 기준 날짜들 설정
        self.today = datetime.now()
        self.today_str = self.today.strftime("%Y%m%d")
        self.yesterday = (self.today - timedelta(days=1)).strftime("%Y%m%d")
        self.tomorrow = (self.today + timedelta(days=1)).strftime("%Y%m%d")
        self.one_month_ago = (self.today - timedelta(days=30)).strftime("%Y%m%d")
        self.one_month_later = (self.today + timedelta(days=30)).strftime("%Y%m%d")
    
    def test_basic_date_extraction(self):
        # 간단한 날짜 조건이 있는 쿼리
        query = f"SELECT * FROM aicfo_get_all_amt WHERE reg_dt = '{self.yesterday}'"
        from_date, to_date = self.extractor.extract_dates(query)
        
        assert from_date == self.yesterday
        assert to_date == self.yesterday
        
    def test_between_date_extraction(self):
        # BETWEEN 조건이 있는 쿼리
        query = f"SELECT * FROM aicfo_get_all_amt WHERE reg_dt BETWEEN '{self.one_month_ago}' AND '{self.yesterday}'"
        from_date, to_date = self.extractor.extract_dates(query)
        
        assert from_date == self.one_month_ago
        assert to_date == self.yesterday
        
    def test_greater_than_date_extraction(self):
        # 부등호 조건이 있는 쿼리
        query = f"SELECT * FROM aicfo_get_all_amt WHERE reg_dt > '{self.one_month_ago}'"
        from_date, to_date = self.extractor.extract_dates(query)
        
        # reg_dt > date 조건은 date의 다음 날부터 오늘까지가 범위
        expected_from = (datetime.strptime(self.one_month_ago, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
        assert from_date == expected_from
        assert to_date == self.today_str
        
    def test_less_than_date_extraction(self):
        # 부등호 조건이 있는 쿼리
        query = f"SELECT * FROM aicfo_get_all_amt WHERE reg_dt < '{self.yesterday}'"
        from_date, to_date = self.extractor.extract_dates(query)
        
        # reg_dt < date 조건은 오래된 날짜부터 date의 전날까지가 범위
        expected_to = (datetime.strptime(self.yesterday, "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")
        assert from_date == "19700101"  # 가장 과거 날짜
        assert to_date == expected_to
        
    def test_no_date_condition(self):
        # 날짜 조건이 없는 쿼리
        query = "SELECT * FROM aicfo_get_all_amt WHERE acct_no = '1234567890'"
        from_date, to_date = self.extractor.extract_dates(query)
        
        # 날짜 조건이 없으면 오늘 날짜가 기본값
        assert from_date == self.today_str
        assert to_date == self.today_str
        
    def test_future_date_handling(self):
        # 미래 날짜 조건이 있는 쿼리
        query = f"SELECT * FROM aicfo_get_all_amt WHERE reg_dt = '{self.tomorrow}'"
        from_date, to_date = self.extractor.extract_dates(query)
        
        # 미래 날짜도 그대로 추출되어야 함 (실제 처리는 view_table에서 함)
        assert from_date == self.tomorrow
        assert to_date == self.tomorrow
        
    def test_trsc_table_date_column(self):
        # trsc 테이블은 trsc_dt가 기본 날짜 컬럼
        query = f"SELECT * FROM aicfo_get_all_trsc WHERE trsc_dt = '{self.yesterday}'"
        from_date, to_date = self.extractor_trsc.extract_dates(query)
        
        assert from_date == self.yesterday
        assert to_date == self.yesterday
        
    def test_due_date_extraction(self):
        # due_dt 조건이 있는 쿼리
        query = f"""
        SELECT * FROM aicfo_get_all_amt 
        WHERE reg_dt >= '{self.one_month_ago}' AND due_dt = '{self.yesterday}'
        """
        from_date, to_date = self.extractor.extract_dates(query)
        
        assert from_date == self.one_month_ago
        assert to_date == self.today_str
        
    def test_due_date_no_effect(self):
        # due_dt 조건이 있지만 reg_dt보다 나중인 경우
        query = f"""
        SELECT * FROM aicfo_get_all_amt 
        WHERE reg_dt >= '{self.one_month_ago}' AND due_dt = '{self.tomorrow}'
        """
        from_date, to_date = self.extractor.extract_dates(query)
        
        # due_dt가 reg_dt보다 이후이므로, from_date는 변경되지 않아야 함
        assert from_date == self.one_month_ago
        assert to_date == self.today_str
        
    def test_due_date_between(self):
        # due_dt BETWEEN 조건
        query = f"""
        SELECT * FROM aicfo_get_all_amt 
        WHERE reg_dt >= '{self.yesterday}' AND due_dt BETWEEN '{self.one_month_ago}' AND '{self.tomorrow}'
        """
        from_date, to_date = self.extractor.extract_dates(query)
        
        # due_dt의 시작이 reg_dt보다 이전이므로, from_date가 변경되어야 함
        assert from_date == self.one_month_ago
        assert to_date == self.today_str
        
    def test_due_date_greater_than(self):
        # due_dt > 조건
        query = f"""
        SELECT * FROM aicfo_get_all_amt 
        WHERE reg_dt >= '{self.yesterday}' AND due_dt > '{self.one_month_ago}'
        """
        from_date, to_date = self.extractor.extract_dates(query)
        
        # due_dt > one_month_ago는 다음 날부터이므로
        expected_from = (datetime.strptime(self.one_month_ago, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
        
        # 만약 expected_from이 reg_dt보다 이전이면, from_date가 변경되어야 함
        assert from_date == expected_from
        assert to_date == self.today_str
        
    def test_multiple_date_conditions(self):
        # 여러 날짜 조건이 있는 경우
        query = f"""
        SELECT * FROM aicfo_get_all_amt 
        WHERE reg_dt >= '{self.one_month_ago}' 
        AND reg_dt <= '{self.yesterday}'
        AND due_dt = '{self.one_month_ago}'
        """
        from_date, to_date = self.extractor.extract_dates(query)
        
        # reg_dt >= one_month_ago AND reg_dt <= yesterday AND due_dt = one_month_ago
        # due_dt와 reg_dt의 시작이 같으므로 변화 없음
        assert from_date == self.one_month_ago
        assert to_date == self.yesterday
        
    def test_combine_reg_dt_and_due_dt(self):
        # reg_dt와 due_dt 조건이 같이 있지만 due_dt가 더 최근인 경우
        query = f"""
        SELECT * FROM aicfo_get_all_amt 
        WHERE reg_dt >= '{self.one_month_ago}' 
        AND due_dt >= '{self.yesterday}'
        """
        from_date, to_date = self.extractor.extract_dates(query)
        
        # due_dt가 reg_dt보다 이후이므로 영향 없음
        assert from_date == self.one_month_ago
        assert to_date == self.today_str
        
    def test_determine_date_range(self):
        # DateCondition과 _determine_date_range 메서드 직접 테스트
        date_conditions = [
            DateCondition(column="reg_dt", operator="GTE", value=self.one_month_ago)
        ]
        due_date_conditions = [
            DateCondition(column="due_dt", operator="EQ", value=self.yesterday)
        ]
        
        date_range = self.extractor._determine_date_range(date_conditions, due_date_conditions)
        
        # due_dt가 reg_dt보다 이후이므로 영향 없음
        if self.yesterday < self.one_month_ago:
            assert date_range.from_date == self.yesterday
        else:
            assert date_range.from_date == self.one_month_ago
        assert date_range.to_date == self.today_str
        
    def test_no_date_conditions_with_due_dt(self):
        # reg_dt 조건은 없고 due_dt 조건만 있는 경우
        query = f"""
        SELECT * FROM aicfo_get_all_amt 
        WHERE due_dt = '{self.yesterday}'
        """
        from_date, to_date = self.extractor.extract_dates(query)
        
        # due_dt 조건만 있을 때 from_date는 due_dt가 되어야 함
        assert from_date == self.yesterday
        assert to_date == self.today_str