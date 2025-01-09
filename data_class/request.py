from pydantic import BaseModel


class Input(BaseModel):
    user_question: str
    user_id: str = 'default_user'
    session_id: str = 'default_session'
 
class Output(BaseModel):
    status: int# 200
    success: bool# True
    retCd: int # 200 
    session_id: str # 해당 그래프의 세션id
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
    node_nm: str
    prompt_nm: str
    prompt: str