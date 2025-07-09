from typing import TypedDict, Tuple, List, Dict, Any
from fastapi import WebSocket

class ProcessingFlags(TypedDict):
    is_joy: bool
    is_opendue: bool
    no_data: bool
    note_changed: bool
    future_date: bool
    invalid_date: bool
    query_error: bool
    query_changed: bool
    has_next: bool
    safe_count: int

class VectorNotes(TypedDict):
    origin_note: str
    vector_notes: List[str]
    
class GraphState(TypedDict):
    chain_id: str
    trace_id: str
    user_info: Tuple[str, str]
    company_id: str
    user_question: str
    is_api: bool
    selected_api: str
    selected_table: str
    sql_query: str
    sql_error: str
    date_info: Tuple[str, str]
    query_result: Dict[str, Any]
    fstring_answer: str
    table_pipe: str
    final_answer: str
    total_rows: int
    vector_notes: VectorNotes
    websocket: WebSocket
    flags: ProcessingFlags