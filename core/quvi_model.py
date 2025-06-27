from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Tuple


class Input(BaseModel):
    user_question: str
    user_id: str
    session_id: str
    use_intt_id: str
    company_id: str

class AnswerBody(BaseModel):
    answer: str
    raw_data: List[Dict[str, Any]]
    session_id: str
    chain_id: str
    recommend: List[str]
    is_api: bool
    date_info: Optional[Tuple[Optional[str], Optional[str]]]
    sql_query: Optional[str]
    selected_table: Optional[str]
    has_next: bool
    profile: Dict[str, Any]

class Output(BaseModel):
    status: int     # HTTP 상태 코드
    success: bool   # 성공 여부
    retCd: int      # 응답 코드
    message: str    # 응답 메시지
    body: AnswerBody  # 응답 본문