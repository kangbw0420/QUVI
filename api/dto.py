from typing import List, Dict, Any

from pydantic import BaseModel


class CompanyInfo(BaseModel):
    custApiDv: str
    custNm: str
    isMainYn: str

class Input(BaseModel):
    user_question: str
    user_id: str = 'daquv03'
    session_id: str = 'default_session'
    use_intt_id: str
    access_company_list: List[CompanyInfo]


class Output(BaseModel):
    status: int# 200
    success: bool# True
    retCd: int # 200 
    message: str# 질답 성공
    body: dict # 본문


class PostgreToVectorData(BaseModel):
    title: str = ""
    shot: str = ""
    id: str = ""
    del_yn: str = "N"


class VectorDataQuery(BaseModel):
    collection_name: str
    query_text: str
    top_k: int = 1


class PromptInput(BaseModel):
    node_nm: str
    prompt_nm: str
    prompt: str = ""


class FewshotInput(BaseModel):
    title: str = ""
    shots: str = ""


class DocumentRequest(BaseModel):
    collection_name: str = ""
    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []


class MappingRequest(BaseModel):
    idx: int = 0
    originalTitle: str = ""
    replaceTitle: str = ""
    type: str = ""
    align: str = ""

class VocRequest(BaseModel):
    seq: int = 0
    userId: str = ""
    companyId: str = ""
    channel: str = ""
    utteranceContents: str = ""
    conversationId: str = ""
    chainId: str = ""
    type: str = ""
    imageUrl: str = ""
    content: str = ""
    answer: str = ""

class StockRequest(BaseModel):
    stockCd: str = ""
    stockNm: str = ""
    stockNickNm: str = ""
    stockNickNmList: List[str] = []
