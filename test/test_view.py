import pytest
from datetime import datetime
from utils.query.view.classify_query import QueryClassifier
from utils.query.view.extract_date import DateExtractor, extract_view_date
from utils.query.view.view_table import ViewTableTransformer, add_view_table

class TestViewTransformation:
    @pytest.fixture
    def test_params(self):
        return {
            'user_info': ('test_user', 'test_intt'),
            'view_com': 'test_company',
            'today': '2024-02-21',
            'flags': {'future_date': False, 'past_date': False}
        }

    def test_sum_group_by_with_future_date(self, test_params):
        query = """
        SELECT note1, SUM(trsc_amt) AS total_in_amt 
        FROM aicfo_get_all_trsc 
        WHERE view_dv = '수시' 
        AND curr_cd = 'KRW' 
        AND in_out_dv = '입금' 
        AND trsc_dt BETWEEN '20250101' AND '20250113' 
        GROUP BY note1 
        ORDER BY total_in_amt DESC 
        LIMIT 1
        """
        
        # 1. Test query classification
        classifier = QueryClassifier()
        info = classifier.classify_query(query)
        assert not info.has_union
        assert not info.has_subquery
        assert 'aicfo_get_all_trsc' in info.table_names
        
        # 2. Test date extraction
        extractor = DateExtractor('trsc', test_params['today'])
        from_date, to_date = extractor.extract_dates(query)
        assert extractor.flags['future_date']  # Should detect future date
        assert from_date <= test_params['today'].replace('-', '')
        assert to_date <= test_params['today'].replace('-', '')
        
        # 3. Test full transformation
        transformed = add_view_table(
            query=query,
            selected_table='trsc',
            view_com=test_params['view_com'],
            user_info=test_params['user_info'],
            view_date=(from_date, to_date),
            flags=test_params['flags']
        )
        
        # Verify transformation
        assert 'AICFO_GET_ALL_TRSC(' in transformed
        assert all(param in transformed for param in test_params['user_info'])
        assert test_params['view_com'] in transformed
        assert from_date in transformed
        assert to_date in transformed

    def test_date_trunc_with_between(self, test_params):
        query = """
        SELECT TO_CHAR(DATE_TRUNC('month', trsc_dt::timestamp), 'YYYYMM') AS trsc_month,
        SUM(CASE WHEN in_out_dv = '출금' THEN trsc_amt ELSE 0 END) AS total_outgoing_amount
        FROM aicfo_get_all_trsc
        WHERE view_dv = '수시'
        AND curr_cd = 'KRW'
        AND trsc_dt BETWEEN '20241201' AND '20250113'
        GROUP BY trsc_month
        """
        
        info = QueryClassifier.classify_query(query)
        assert not info.has_union
        assert not info.has_subquery
        
        extractor = DateExtractor('trsc', test_params['today'])
        from_date, to_date = extractor.extract_dates(query)
        assert extractor.flags['future_date']
        
        transformed = add_view_table(
            query=query,
            selected_table='trsc',
            view_com=test_params['view_com'],
            user_info=test_params['user_info'],
            view_date=(from_date, to_date),
            flags=test_params['flags']
        )
        
        assert 'DATE_TRUNC' in transformed
        assert 'trsc_month' in transformed
        assert 'GROUP BY' in transformed

    def test_like_pattern_with_single_date(self, test_params):
        query = """
        SELECT bank_nm, acct_no, trsc_dt, trsc_tm, note1, in_out_dv, trsc_amt, trsc_bal
        FROM aicfo_get_all_trsc
        WHERE view_dv = '수시'
        AND curr_cd = 'KRW'
        AND in_out_dv = '출금'
        AND note1 LIKE '%웹케시%'
        AND trsc_dt = '20240218'
        """
        
        info = QueryClassifier.classify_query(query)
        assert not info.has_union
        assert not info.has_subquery
        assert "LIKE" in query
        
        transformed = add_view_table(
            query=query,
            selected_table='trsc',
            view_com=test_params['view_com'],
            user_info=test_params['user_info'],
            view_date=('20240218', '20240218'),
            flags=test_params['flags']
        )
        
        assert 'LIKE' in transformed
        assert '%웹케시%' in transformed

    def test_amt_table_with_multiple_conditions(self, test_params):
        query = """
        SELECT bank_nm, acct_dv, acct_no, acct_bal_amt, open_dt, due_dt, intr_rate, acct_bal_upd_dtm
        FROM aicfo_get_all_amt
        WHERE view_dv = '예적금'
        AND curr_cd = 'KRW'
        AND reg_dt = '20240928'
        """
        
        info = QueryClassifier.classify_query(query)
        assert not info.has_union
        assert not info.has_subquery
        assert 'aicfo_get_all_amt' in info.table_names
        
        extractor = DateExtractor('amt', test_params['today'])
        from_date, to_date = extractor.extract_dates(query)
        assert extractor.flags['future_date']
        
        transformed = add_view_table(
            query=query,
            selected_table='amt',
            view_com=test_params['view_com'],
            user_info=test_params['user_info'],
            view_date=(from_date, to_date),
            flags=test_params['flags']
        )
        
        assert 'aicfo_get_all_amt(' in transformed
        assert all(field in transformed for field in ['bank_nm', 'acct_dv', 'acct_no', 'acct_bal_amt'])

    def test_past_date_handling(self, test_params):
        query = """
        SELECT bank_nm, acct_no, trsc_dt, trsc_tm, note1, in_out_dv, trsc_amt, trsc_bal
        FROM aicfo_get_all_trsc
        WHERE view_dv = '수시'
        AND curr_cd = 'KRW'
        AND trsc_dt = '20190512'
        """
        
        extractor = DateExtractor('trsc', test_params['today'])
        from_date, to_date = extractor.extract_dates(query)
        
        # Verify past date handling
        past_date = datetime.strptime('20190512', '%Y%m%d')
        today = datetime.strptime(test_params['today'], '%Y-%m-%d')
        assert (today - past_date).days > 2
        
        transformed = add_view_table(
            query=query,
            selected_table='trsc',
            view_com=test_params['view_com'],
            user_info=test_params['user_info'],
            view_date=(from_date, to_date),
            flags=test_params['flags']
        )
        
        assert 'AICFO_GET_ALL_TRSC(' in transformed

    def test_complex_conditions_with_date_range(self, test_params):
        query = """
        SELECT TO_CHAR(DATE_TRUNC('month', trsc_dt::timestamp), 'YYYYMM') AS trsc_month,
        SUM(trsc_amt) AS total_trsc_amt
        FROM aicfo_get_all_trsc
        WHERE view_dv = '수시'
        AND curr_cd = 'KRW'
        AND trsc_dt BETWEEN '20181201' AND '20190505'
        AND in_out_dv = '출금'
        AND (note1 LIKE '%급여%' OR note1 LIKE '%인건비%' OR note1 LIKE '%월급%')
        GROUP BY trsc_month
        """
        
        info = QueryClassifier.classify_query(query)
        assert not info.has_union
        assert not info.has_subquery
        assert 'LIKE' in query
        assert 'BETWEEN' in query
        
        extractor = DateExtractor('trsc', test_params['today'])
        from_date, to_date = extractor.extract_dates(query)
        
        transformed = add_view_table(
            query=query,
            selected_table='trsc',
            view_com=test_params['view_com'],
            user_info=test_params['user_info'],
            view_date=(from_date, to_date),
            flags=test_params['flags']
        )
        
        assert 'DATE_TRUNC' in transformed
        assert 'OR' in transformed
        assert 'LIKE' in transformed
        assert 'GROUP BY' in transformed

    def test_multiple_like_conditions_with_aliases(self, test_params):
        query = """
        SELECT a.bank_nm, a.acct_no, a.trsc_dt, a.trsc_tm, 
               a.note1, a.in_out_dv, a.trsc_amt, a.trsc_bal
        FROM aicfo_get_all_trsc a
        WHERE a.view_dv = '수시'
        AND a.curr_cd = 'KRW'
        AND a.in_out_dv = '출금'
        AND (a.note1 LIKE '%급여%' OR a.note1 LIKE '%인건비%')
        AND a.trsc_dt BETWEEN '20240101' AND '20240131'
        """
        
        info = QueryClassifier.classify_query(query)
        assert not info.has_union
        assert not info.has_subquery
        assert 'aicfo_get_all_trsc' in info.table_names
        
        transformed = add_view_table(
            query=query,
            selected_table='trsc',
            view_com=test_params['view_com'],
            user_info=test_params['user_info'],
            view_date=('20240101', '20240131'),
            flags=test_params['flags']
        )
        
        # 별칭이 올바르게 유지되는지 확인
        assert 'AICFO_GET_ALL_TRSC(' in transformed
        assert 'AS a' in transformed
        assert 'a.note1' in transformed

    def test_join_with_subquery(self, test_params):
        query = """
        WITH monthly_totals AS (
            SELECT acct_no, bank_nm, SUM(trsc_amt) as total_amt
            FROM aicfo_get_all_trsc
            WHERE trsc_dt BETWEEN '20240101' AND '20240131'
            AND in_out_dv = '출금'
            GROUP BY acct_no, bank_nm
        )
        SELECT t.bank_nm, t.acct_no, t.total_amt, a.acct_bal_amt
        FROM monthly_totals t
        JOIN aicfo_get_all_amt a ON t.acct_no = a.acct_no
        WHERE a.reg_dt = '20240131'
        """
        
        info = QueryClassifier.classify_query(query)
        assert info.has_joins
        assert 'aicfo_get_all_trsc' in info.table_names
        assert 'aicfo_get_all_amt' in info.table_names
        
        transformed = add_view_table(
            query=query,
            selected_table='amt',  # 주 테이블 기준
            view_com=test_params['view_com'],
            user_info=test_params['user_info'],
            view_date=('20240131', '20240131'),
            flags=test_params['flags']
        )
        
        # CTE와 JOIN이 올바르게 변환되었는지 확인
        assert 'WITH monthly_totals' in transformed
        assert 'JOIN AICFO_GET_ALL_AMT(' in transformed

    def test_union_with_different_date_ranges(self, test_params):
        query = """
        SELECT bank_nm, acct_no, trsc_dt, trsc_amt
        FROM aicfo_get_all_trsc
        WHERE trsc_dt BETWEEN '20240101' AND '20240131'
        AND in_out_dv = '출금'
        UNION ALL
        SELECT bank_nm, acct_no, trsc_dt, trsc_amt
        FROM aicfo_get_all_trsc
        WHERE trsc_dt BETWEEN '20240201' AND '20240229'
        AND in_out_dv = '입금'
        """
        
        info = QueryClassifier.classify_query(query)
        assert info.has_union
        assert not info.has_subquery
        
        transformed = add_view_table(
            query=query,
            selected_table='trsc',
            view_com=test_params['view_com'],
            user_info=test_params['user_info'],
            view_date=('20240101', '20240229'),
            flags=test_params['flags']
        )
        
        # UNION ALL이 유지되고 각 부분이 올바르게 변환되었는지 확인
        assert 'UNION ALL' in transformed
        assert transformed.count('AICFO_GET_ALL_TRSC(') == 2

    def test_nested_subqueries_with_aggregation(self, test_params):
        query = """
        SELECT bank_nm, acct_no, 
               (SELECT AVG(trsc_amt) 
                FROM aicfo_get_all_trsc b 
                WHERE b.acct_no = a.acct_no 
                AND b.trsc_dt BETWEEN '20240101' AND '20240131') as avg_amt
        FROM aicfo_get_all_trsc a
        WHERE a.trsc_dt = '20240131'
        AND EXISTS (
            SELECT 1 
            FROM aicfo_get_all_trsc c 
            WHERE c.acct_no = a.acct_no 
            AND c.trsc_dt >= '20240101'
            AND c.trsc_amt > 1000000
        )
        """
        
        info = QueryClassifier.classify_query(query)
        assert info.has_subquery
        assert info.subquery_count >= 2
        
        transformed = add_view_table(
            query=query,
            selected_table='trsc',
            view_com=test_params['view_com'],
            user_info=test_params['user_info'],
            view_date=('20240101', '20240131'),
            flags=test_params['flags']
        )
        
        # 중첩 서브쿼리가 올바르게 변환되었는지 확인
        assert transformed.count('AICFO_GET_ALL_TRSC(') >= 3
        assert 'EXISTS' in transformed
        assert 'AVG' in transformed

    def test_complex_window_functions(self, test_params):
        query = """
        SELECT bank_nm, acct_no, trsc_dt, trsc_amt,
               SUM(trsc_amt) OVER (PARTITION BY acct_no ORDER BY trsc_dt) as running_total,
               LAG(trsc_amt) OVER (PARTITION BY acct_no ORDER BY trsc_dt) as prev_amt
        FROM aicfo_get_all_trsc
        WHERE trsc_dt BETWEEN '20240101' AND '20240131'
        AND curr_cd = 'KRW'
        """
        
        info = QueryClassifier.classify_query(query)
        assert not info.has_union
        assert not info.has_subquery
        
        transformed = add_view_table(
            query=query,
            selected_table='trsc',
            view_com=test_params['view_com'],
            user_info=test_params['user_info'],
            view_date=('20240101', '20240131'),
            flags=test_params['flags']
        )
        
        # 윈도우 함수가 올바르게 유지되는지 확인
        assert 'OVER (PARTITION BY' in transformed
        assert 'LAG' in transformed
        assert 'running_total' in transformed

    def test_mixed_date_and_due_date_conditions(self, test_params):
        query = """
        SELECT bank_nm, acct_no, acct_bal_amt, due_dt
        FROM aicfo_get_all_amt
        WHERE reg_dt BETWEEN '20240101' AND '20240331'
        AND due_dt >= '20240630'
        AND curr_cd = 'KRW'
        AND view_dv = '예적금'
        """
        
        info = QueryClassifier.classify_query(query)
        assert not info.has_union
        assert not info.has_subquery
        
        extractor = DateExtractor('amt', test_params['today'])
        from_date, to_date = extractor.extract_dates(query)
        
        transformed = add_view_table(
            query=query,
            selected_table='amt',
            view_com=test_params['view_com'],
            user_info=test_params['user_info'],
            view_date=(from_date, to_date),
            flags=test_params['flags']
        )
        
        # reg_dt와 due_dt 조건이 모두 유지되는지 확인
        assert 'reg_dt BETWEEN' in transformed
        assert 'due_dt >=' in transformed
        assert 'aicfo_get_all_amt(' in transformed