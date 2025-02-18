import json
from utils.config import Config
import httpx

BASE_URL = Config.VECTOR_STORE_DOMAIN

async def check_joy(query_text: str) -> dict:

    url = f"{BASE_URL}/checkpoint/{query_text}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            results = response.json()
            """results = 
            {
                "text": "안녕하세요.",
                "checkpoint": 'joy'
            }
            """
            print(f"[SUCCESS] Get Embedding results:\n{json.dumps(results, indent=2, ensure_ascii=False)}")
            return results
        except httpx.HTTPError as e:
            print(f"[ERROR] Failed to test embedding: {e}")