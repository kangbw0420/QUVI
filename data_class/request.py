from pydantic import BaseModel


class Input(BaseModel):
    user_question: str
    user_id: str = 'daquv03'
    session_id: str = 'default_session'
 
class Output(BaseModel):
    status: int# 200
    success: bool# True
    retCd: int # 200 
    message: str# 질답 성공
    body: dict # 본문


class PostgreToVectorData(BaseModel):
    collection_name: str
    id: str = "0"
    document: str = ""
    del_yn: str = "N"
    type: str = "C"


class VectorDataQuery(BaseModel):
    collection_name: str
    query_text: str
    top_k: str


class PromptInput(BaseModel):
    node_nm: str
    prompt_nm: str
    prompt: str = ""