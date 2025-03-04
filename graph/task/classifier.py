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

async def classify_yqmd(query_text: str, sql_query: str) -> str:
    """연간/분기/월간/일간 파라미터를 결정하여 SQL 쿼리에 추가
    Returns:
        str: 파라미터가 추가된 SQL 쿼리
    """
    url = f"{BASE_URL}/yqmd/{query_text}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            result = response.json()

            print(f"[SUCCESS] Get YQMD classification result:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 응답에서 'y', 'q', 'm', 'd' 중 하나를 받아옴
            classification = result.get("yqmd", "m").upper()  # 기본값은 'm'

            # 마지막 괄호 바로 앞에 새 파라미터 추가
            if sql_query.endswith(')'):
                modified_query = sql_query[:-1] + f", '{classification}'" + ')'
            else:
                # 혹시 쿼리가 예상 형식이 아닐 경우 원본 반환
                modified_query = sql_query
                
            print(f"[YQMD] Modified query: {modified_query}")
            return modified_query

        except httpx.HTTPError as e:
            print(f"[ERROR] Failed to get YQMD classification: {e}")
            # 에러 발생 시 기본값 'M' 사용
            if sql_query.endswith(')'):
                return sql_query[:-1] + ", 'M')"
            else:
                return sql_query