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

            print(f"[SUCCESS] Get Embedding results:\n{json.dumps(results, indent=2, ensure_ascii=False)}")
            return results
        except httpx.HTTPError as e:
            print(f"[ERROR] Failed to test embedding: {e}")

async def is_api(query_text: str) -> str:

    url = f"{BASE_URL}/isapi/{query_text}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            result = response.json()

            print(f"[SUCCESS] Get Embedding results:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
            if result["isapi"] == "1":
                selected_table = "api"
            else:
                selected_table = ""

            return selected_table

        except httpx.HTTPError as e:
            print(f"[ERROR] Failed to test embedding: {e}")