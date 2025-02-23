import pytest
from unittest.mock import patch
from utils.query.ever_note import ever_note

# Mock data for simulating vector search results
NOTE_MAPPINGS = {
    "급여입금": ["월급입금", "급여이체"],
    "식대지원": ["식대", "직원식대"],
    "공과금": ["관리비", "공과금납부"],
    "카드대금": ["카드결제", "신용카드대금"],
    "거래처입금": ["매출입금", "거래처송금"]
}

# Mock the vector search function
async def mock_get_evernote(note_str: str, main_com: str, top_k: int = 1):
    if note_str in NOTE_MAPPINGS:
        return [NOTE_MAPPINGS[note_str][0]]  # Return first match
    return []

@pytest.mark.asyncio
@patch('utils.retriever.retriever.get_evernote', side_effect=mock_get_evernote)
async def test_note1_eq_condition(mock_get):
    """Test replacing simple note1 = 'value' condition"""
    query = "SELECT * FROM trsc WHERE note1 = '급여입금'"
    expected = "SELECT * FROM trsc WHERE note1 = '월급입금'"
    
    result = await ever_note(query, "test_company")
    
    # Normalize whitespace for comparison
    assert result.lower().replace(" ", "") == expected.lower().replace(" ", "")
    mock_get.assert_called_once_with("급여입금", "test_company")

@pytest.mark.asyncio
@patch('utils.retriever.retriever.get_evernote', side_effect=mock_get_evernote)
async def test_note1_like_condition(mock_get):
    """Test replacing note1 LIKE condition"""
    query = "SELECT * FROM trsc WHERE note1 LIKE '%식대지원%'"
    expected = "SELECT * FROM trsc WHERE note1 LIKE '%식대%'"
    
    result = await ever_note(query, "test_company")
    
    assert result.lower().replace(" ", "") == expected.lower().replace(" ", "")
    mock_get.assert_called_once_with("식대지원", "test_company")

@pytest.mark.asyncio
@patch('utils.retriever.retriever.get_evernote', side_effect=mock_get_evernote)
async def test_multiple_note1_conditions(mock_get):
    """Test replacing multiple note1 conditions"""
    query = """
        SELECT * FROM trsc 
        WHERE note1 = '급여입금' 
        AND trsc_amt > 1000000 
        AND note1 LIKE '%공과금%'
    """
    expected = """
        SELECT * FROM trsc 
        WHERE note1 = '월급입금' 
        AND trsc_amt > 1000000 
        AND note1 LIKE '%관리비%'
    """
    
    result = await ever_note(query, "test_company")
    
    assert result.lower().replace(" ", "") == expected.lower().replace(" ", "")
    assert mock_get.call_count == 2  # Should be called twice for two note1 conditions

@pytest.mark.asyncio
@patch('utils.retriever.retriever.get_evernote', side_effect=mock_get_evernote)
async def test_subquery_with_note1(mock_get):
    """Test replacing note1 conditions in subquery"""
    query = """
        SELECT * FROM trsc t1 
        WHERE note1 = '카드대금' 
        AND EXISTS (
            SELECT 1 FROM trsc t2 
            WHERE t2.note1 LIKE '%거래처입금%' 
            AND t1.trsc_dt = t2.trsc_dt
        )
    """
    expected = """
        SELECT * FROM trsc t1 
        WHERE note1 = '카드결제' 
        AND EXISTS (
            SELECT 1 FROM trsc t2 
            WHERE t2.note1 LIKE '%매출입금%' 
            AND t1.trsc_dt = t2.trsc_dt
        )
    """
    
    result = await ever_note(query, "test_company")
    
    assert result.lower().replace(" ", "") == expected.lower().replace(" ", "")
    assert mock_get.call_count == 2

@pytest.mark.asyncio
@patch('utils.retriever.retriever.get_evernote', side_effect=mock_get_evernote)
async def test_no_note1_condition(mock_get):
    """Test query without note1 conditions"""
    query = "SELECT * FROM trsc WHERE trsc_amt > 1000000"
    
    result = await ever_note(query, "test_company")
    
    assert result.lower().replace(" ", "") == query.lower().replace(" ", "")
    assert not mock_get.called  # Should not call vector search

@pytest.mark.asyncio
@patch('utils.retriever.retriever.get_evernote', side_effect=mock_get_evernote)
async def test_note1_no_vector_match(mock_get):
    """Test handling when no vector matches found"""
    query = "SELECT * FROM trsc WHERE note1 = '존재하지않는내용'"
    
    result = await ever_note(query, "test_company")
    
    # Should return original query unchanged when no matches found
    assert result.lower().replace(" ", "") == query.lower().replace(" ", "")
    mock_get.assert_called_once_with("존재하지않는내용", "test_company")

@pytest.mark.asyncio
@patch('utils.retriever.retriever.get_evernote', side_effect=mock_get_evernote)
async def test_invalid_sql(mock_get):
    """Test handling of invalid SQL"""
    query = "SELECT * FRO trsc WHERE note1 = '급여입금'"  # Intentionally malformed
    
    result = await ever_note(query, "test_company")
    
    # Should return original query unchanged for invalid SQL
    assert result == query
    assert not mock_get.called  # Should not attempt vector search