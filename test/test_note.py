import pytest
import asyncio
from unittest.mock import patch, AsyncMock

from utils.query.ever_note import ever_note


class MockRetriever:
    async def get_evernote(self, note_str, main_com, top_k=1):
        # Mock vector search results for testing
        note_mappings = {
            "입금": ["입금(계좌이체)"],
            "계좌이체": ["계좌이체(보통예금)"],
            "카드": ["카드대금결제"],
            "대출": ["대출이자납입"],
            "환불": ["상품대금환불"],
            "급여": ["급여입금"]
        }
        
        # Return mapped note or original if no mapping exists
        return [note_mappings.get(note_str, [note_str])[0]]


@pytest.fixture
def mock_retriever():
    with patch('utils.query.ever_note.retriever', MockRetriever()):
        yield


@pytest.mark.asyncio
async def test_ever_note_single_condition(mock_retriever):
    """Test ever_note with a single note1 condition"""
    # Test query with a simple note1 = '입금' condition
    query = "SELECT * FROM aicfo_get_all_trsc('123', '456', '테스트회사', '20230101', '20230131') WHERE note1 = '입금'"
    
    # Run the function
    result = await ever_note(query, "테스트회사")
    
    # Verify the result
    assert "note1 = '입금(계좌이체)'" in result
    

@pytest.mark.asyncio
async def test_ever_note_multiple_conditions(mock_retriever):
    """Test ever_note with multiple note1 conditions"""
    # Test query with multiple conditions
    query = """
    SELECT * FROM aicfo_get_all_trsc('123', '456', '테스트회사', '20230101', '20230131') 
    WHERE (note1 = '입금' OR note1 = '계좌이체' OR note1 = '카드')
    """
    
    # Run the function
    result = await ever_note(query, "테스트회사")
    
    # Verify all conditions were replaced
    assert "note1 = '입금(계좌이체)'" in result
    assert "note1 = '계좌이체(보통예금)'" in result
    assert "note1 = '카드대금결제'" in result


@pytest.mark.asyncio
async def test_ever_note_like_conditions(mock_retriever):
    """Test ever_note with LIKE conditions"""
    # Test query with LIKE conditions
    query = """
    SELECT * FROM aicfo_get_all_trsc('123', '456', '테스트회사', '20230101', '20230131') 
    WHERE note1 LIKE '%입금%' OR note1 LIKE '%환불%'
    """
    
    # Run the function
    result = await ever_note(query, "테스트회사")
    
    # Verify LIKE conditions were replaced properly
    assert "note1 LIKE '%입금(계좌이체)%'" in result
    assert "note1 LIKE '%상품대금환불%'" in result


@pytest.mark.asyncio
async def test_ever_note_complex_query(mock_retriever):
    """Test ever_note with a complex query structure"""
    # Test with a more complex query
    query = """
    SELECT t.* FROM aicfo_get_all_trsc('123', '456', '테스트회사', '20230101', '20230131') t
    WHERE (t.in_out_dv = '입금' AND t.note1 = '급여')
    OR (t.in_out_dv = '출금' AND t.note1 = '대출')
    ORDER BY t.trsc_dt DESC
    """
    
    # Run the function
    result = await ever_note(query, "테스트회사")
    
    # Verify the result
    assert "t.note1 = '급여입금'" in result
    assert "t.note1 = '대출이자납입'" in result


@pytest.mark.asyncio
async def test_ever_note_no_modification(mock_retriever):
    """Test ever_note with a query that doesn't have note1 conditions"""
    # Test with a query that has no note1 conditions
    query = """
    SELECT * FROM aicfo_get_all_trsc('123', '456', '테스트회사', '20230101', '20230131') 
    WHERE trsc_dt BETWEEN '20230101' AND '20230131'
    """
    
    # Run the function
    result = await ever_note(query, "테스트회사")
    
    # Verify the query wasn't modified
    assert result == query


@pytest.mark.asyncio
async def test_ever_note_with_subquery(mock_retriever):
    """Test ever_note with a query that includes a subquery"""
    # Test with a query that has a subquery containing note1 conditions
    query = """
    SELECT * FROM (
        SELECT * FROM aicfo_get_all_trsc('123', '456', '테스트회사', '20230101', '20230131') 
        WHERE note1 = '입금' OR note1 = '카드'
    ) subq
    WHERE trsc_amt > 100000
    """
    
    # Run the function
    result = await ever_note(query, "테스트회사")
    
    # Verify the note1 conditions in the subquery were modified
    assert "note1 = '입금(계좌이체)'" in result
    assert "note1 = '카드대금결제'" in result


@pytest.mark.asyncio
async def test_ever_note_error_handling(mock_retriever):
    """Test ever_note error handling with invalid SQL"""
    # Test with invalid SQL
    query = "SELECT * FROM invalid query syntax"
    
    # Run the function - should return original query on parse error
    result = await ever_note(query, "테스트회사")
    
    # Verify original query is returned
    assert result == query


@pytest.mark.asyncio
async def test_ever_note_timeout_handling():
    """Test ever_note handling of timeout in vector search"""
    # Mock retriever that simulates a timeout
    class TimeoutRetriever:
        async def get_evernote(self, note_str, main_com, top_k=1):
            await asyncio.sleep(6)  # Exceed the 5 second timeout
            return []
    
    # Patch retriever with our timeout version
    with patch('utils.query.ever_note.retriever', TimeoutRetriever()):
        query = "SELECT * FROM aicfo_get_all_trsc('123', '456', '테스트회사', '20230101', '20230131') WHERE note1 = '입금'"
        
        # Run the function - should return original query after timeout
        result = await ever_note(query, "테스트회사")
        
        # Should contain the original condition since vector search timed out
        assert "note1 = '입금'" in result


@pytest.mark.asyncio
async def test_ever_note_cached_results(mock_retriever):
    """Test ever_note caching of vector search results"""
    # Test with repeated note1 values
    query = """
    SELECT * FROM aicfo_get_all_trsc('123', '456', '테스트회사', '20230101', '20230131') 
    WHERE note1 = '입금' OR note1 = '입금' OR description LIKE '%based on note1 = ''입금''%'
    """
    
    # Create a spy on the get_evernote method to count calls
    spy_retriever = MockRetriever()
    spy_get_evernote = AsyncMock(wraps=spy_retriever.get_evernote)
    spy_retriever.get_evernote = spy_get_evernote
    
    with patch('utils.query.ever_note.retriever', spy_retriever):
        # Run the function
        result = await ever_note(query, "테스트회사")
        
        # Verify the result has all instances replaced
        assert result.count("입금(계좌이체)") >= 2
        
        # Verify get_evernote was called only once for '입금'
        calls = [call for call in spy_get_evernote.call_args_list if call[0][0] == '입금']
        assert len(calls) == 1