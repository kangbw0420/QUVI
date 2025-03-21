import json
import requests
from utils.config import Config
from utils.logger import setup_logger

logger = setup_logger('vector_db')
BASE_URL = Config.VECTOR_STORE_DOMAIN

class EmbeddingAPIClient:

    def query_embedding(collection_name: str, query_text: str, top_k: int = 5):
        """
        서버에서 텍스트를 검색하는 함수
        """
        url = f"{BASE_URL}/query"
        payload = {
            "collection_name": collection_name,
            "query_text": query_text,
            "top_k": top_k
        }

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()

            results = response.json()
            logger.info(f"Query successful with {len(results.get('results', {}).get('documents', [[]]))} results")

            if logger.isEnabledFor(10):  # DEBUG level
                logger.debug(f"Query results:\n{json.dumps(results, indent=2, ensure_ascii=False)}")

            return results
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to query embedding: {e}")
            return None

    def get_embedding(collection_name: str):
        """
        서버에서 데이터를 조회하는 함수
        """
        url = f"{BASE_URL}/get/{collection_name}"

        try:
            response = requests.get(url)
            response.raise_for_status()

            results = response.json()
            logger.info(f"Successfully retrieved embedding for {collection_name}")

            if logger.isEnabledFor(10):  # DEBUG level
                logger.debug(f"Embedding results:\n{json.dumps(results, indent=2, ensure_ascii=False)}")

            return results
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get embedding: {e}")
            return None

    def getAll_embedding(self):
        """
        서버에서 전체 데이터를 조회하는 함수
        """
        url = f"{BASE_URL}/get/all"

        try:
            response = requests.get(url)
            response.raise_for_status()

            results = response.json()
            # print(f"[SUCCESS] Get All Embedding results:\n{json.dumps(results, indent=2, ensure_ascii=False)}")

            return results["collections"]
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get all embeddings: {e}")
            return []

    def add_embedding(collection_name: str, ids: list[str], documents: list[str], metadatas: list[dict]):
        """
        서버에 임베딩 데이터를 추가하는 함수
        """
        url = f"{BASE_URL}/add"
        payload = {
            "collection_name": collection_name,
            "ids": ids,
            "documents": documents,
            "metadatas": metadatas
        }

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()  # 오류 발생 시 예외 처리

            logger.info(f"Successfully added embeddings to {collection_name}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to add embedding to {collection_name}: {e}")

    def update_embedding(collection_name: str, item_id: str, text: str):
        """
        서버에 기존 데이터를 업데이트하는 함수
        """
        url = f"{BASE_URL}/update"
        payload = {
            "collection_name": collection_name,
            "id": item_id,
            "text": text
        }

        try:
            response = requests.put(url, json=payload)
            response.raise_for_status()

            logger.info(f"Successfully updated embedding")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update embedding: {e}")

    def delete_embedding(collection_name: str, item_id: str):
        """
        서버에서 특정 ID의 데이터를 삭제하는 함수
        """
        url = f"{BASE_URL}/delete/{collection_name}/{item_id}"

        try:
            response = requests.delete(url)
            response.raise_for_status()

            logger.info(f"Successfully deleted embedding")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to delete embedding: {e}")

    def collection_delete_embedding(collection_name: str):
        """
        서버에서 ID 리스트의 데이터를 삭제하는 함수
        """
        url = f"{BASE_URL}/collectionDelete"
        payload = {
            "collection_name": collection_name,
        }

        try:
            response = requests.delete(url, json=payload)
            response.raise_for_status()

            logger.info(f"Successfully deleted collection {collection_name}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")