from typing import TypedDict, Tuple, List

class ProcessingFlags(TypedDict):
    is_joy: bool
    no_data: bool
    note_changed: bool
    future_date: bool
    query_date: bool
    query_error: bool
    query_changed: bool
    # stock_sec: bool
    # past_date: bool

class VectorNotes(TypedDict):
    origin_note: str
    vector_notes: List[str]
    
class GraphState(TypedDict):
    chain_id: str
    trace_id: str
    user_info: Tuple[str, str]
    company_id: str
    yogeumjae: str # debugging: 이제 필요 없지만 fstring을 전달하기 위한 흔적 기관
    # shellder: boolean
    user_question: str
    selected_table: str
    selected_api: str
    sql_query: str
    sql_error: str
    column_list: List[str] # debug: 회사 내려오는 방식 변경되면 수정
    date_info: Tuple[str, str]
    query_result: dict
    final_answer: str
    vector_notes: VectorNotes
    flags: ProcessingFlags
    # last_data: List[Dict[str, str]] # 이전 3개 그래프의 사용자 질문, 답변, SQL 쿼리