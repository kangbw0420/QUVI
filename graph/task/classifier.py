import re
import json
from typing import List
from utils.config import Config
import httpx
from utils.logger import setup_logger

logger = setup_logger('classifier')
BASE_URL = Config.VECTOR_STORE_DOMAIN

def sanitize_query(query_text: str) -> str:
    # 슬래시, 백슬래시, 따옴표 등 URL에 문제가 될 수 있는 특수 문자를 언더스코어로 변환
    sanitized = re.sub(r'[\\/"\'&?#]', '-', query_text)
    return sanitized

async def check_joy(query_text: str) -> dict:
    sanitized_query = sanitize_query(query_text)
    url = f"{BASE_URL}/checkpoint/{sanitized_query}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            results = response.json()

            logger.info(f"Classification result: {results.get('checkpoint', 'unknown')}")
            if logger.isEnabledFor(10):  # DEBUG level
                logger.debug(f"Full classification results: {json.dumps(results, indent=2, ensure_ascii=False)}")

            return results
        except httpx.HTTPError as e:
            logger.error(f"Error checking joy: {e}")
            # 에러 시 기본값 반환
            return {"checkpoint": "fin"}  # 기본값은 금융 관련 질문으로 설정


async def is_api(query_text: str) -> List[str]:
    sanitized_query = sanitize_query(query_text)
    url = f"{BASE_URL}/isapi/{sanitized_query}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            result = response.json()

            logger.info(f"API classification result: {result.get('isapi', '0')}")
            if logger.isEnabledFor(10):  # DEBUG level
                logger.debug(f"Full API classification results: {json.dumps(result, indent=2, ensure_ascii=False)}")

            if result["isapi"] == "1":
                selected_table = ["api"]
            else:
                selected_table = []

            return selected_table

        except httpx.HTTPError as e:
            logger.error(f"Error checking if query is API: {e}")
            return ""  # 에러 시 빈 문자열 반환

async def classify_yqmd(query_text: str, sql_query: str) -> str:
    """연간/분기/월간/일간 파라미터를 결정하여 SQL 쿼리에 추가
    Returns:
        str: 파라미터가 추가된 SQL 쿼리
    """
    logger.info(f"Classifying YQMD parameter for query: '{query_text[:50]}...'")
    sanitized_query = sanitize_query(query_text)
    url = f"{BASE_URL}/yqmd/{sanitized_query}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            result = response.json()

            logger.info(f"YQMD classification result: {result.get('yqmd', 'm')}")
            if logger.isEnabledFor(10):  # DEBUG level
                logger.debug(f"Full YQMD classification results: {json.dumps(result, indent=2, ensure_ascii=False)}")

            # 응답에서 'y', 'q', 'm', 'd' 중 하나를 받아옴
            classification = result.get("yqmd", "m").upper()  # 기본값은 'm'

            # 마지막 괄호 바로 앞에 새 파라미터 추가
            if sql_query.endswith(')'):
                modified_query = sql_query[:-1] + f", '{classification}'" + ')'
            else:
                # 혹시 쿼리가 예상 형식이 아닐 경우 원본 반환
                modified_query = sql_query
                logger.warning("Query doesn't end with ')', couldn't add YQMD parameter")

            logger.debug(f"Modified query: {modified_query}")
            return modified_query

        except httpx.HTTPError as e:
            logger.error(f"Error classifying YQMD: {e}")
            # 에러 발생 시 기본값 'M' 사용
            if sql_query.endswith(')'):
                return sql_query[:-1] + ", 'M')"
            else:
                return sql_query