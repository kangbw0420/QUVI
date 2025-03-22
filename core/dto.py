from pydantic import BaseModel

class Input(BaseModel):
    user_question: str
    user_id: str
    session_id: str
    use_intt_id: str
    company_id: str

class Output(BaseModel):
    status: int     # 200
    success: bool   # True
    retCd: int      # 200
    message: str    # 질답 성공
    body: dict      # 본문