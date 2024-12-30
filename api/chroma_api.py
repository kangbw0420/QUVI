from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from utils.config import Config

app = FastAPI()

class QueryItem(BaseModel):
    collection_name: str
    query_text: str
    top_k: int = 8

@app.post("/query")
async def query_embeddings(query: QueryItem):
    """임베딩을 쿼리하여 유사한 문서를 검색합니다."""
    try:
        response = requests.post(
            f"{Config.VECTOR_STORE_DOMAIN}/query",
            json=query.dict()
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error communicating with ChromaDB: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)