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