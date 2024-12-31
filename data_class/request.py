from pydantic import BaseModel


class RequestData(BaseModel):
    user_question: str


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
