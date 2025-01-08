from pydantic import BaseModel
from typing import Optional

class Input(BaseModel):
    user_question: str
    user_id: str = 'default_user'
    session_id:str = 'default_session'
    last_question: Optional[str]  # 이전 그래프의 사용자 질문
    last_answer: Optional[str]    # 이전 그래프의 LLM 답변
    last_sql_query: Optional[str] # 이전 그래프의 SQL 쿼리


class Output(BaseModel):
    status: int# 200
    success: bool# True
    retCd: int # 200 
    message: str# 질답 성공
    body: dict # 본문


class PostgreToVectorData(BaseModel):
    collection_name: str
    item_id: str
    text: str
    type: str = "C"
    del_yn: str = "N"


class VectorDataQuery(BaseModel):
    collection_name: str
    query_text: str
    top_k: str


class PromptInput(BaseModel):
    prompt_name: str
    prompt: str
