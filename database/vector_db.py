import requests
import json
from utils.config import Config

BASE_URL = Config.VECTOR_STORE_DOMAIN

class EmbeddingAPIClient:
    @staticmethod
    def test_embedding(collection_name: str):
        url = f"{BASE_URL}/get/all/{collection_name}"

        try:
            response = requests.get(url)
            print(f"[SUCCESS] Embedding test: {response.json()}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to test embedding: {e}")

    @staticmethod
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
            print(f"[SUCCESS] Embedding added: {response.json()}")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to add embedding: {e}")

    @staticmethod
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
            print(f"[SUCCESS] Embedding updated: {response.json()}")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to update embedding: {e}")

    @staticmethod
    def query_embedding(collection_name: str, query_text: str, top_k: int = 5):
        """
        서버에서 텍스트를 검색하는 함수
        """

        print("111 ===> " )
        url = f"{BASE_URL}/query"
        print("222 ===> ", url)
        payload = {
            "collection_name": collection_name,
            "query_text": query_text,
            "top_k": top_k
        }
        print("333 ===> ", payload)


        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            results = response.json()
            print(f"[SUCCESS] Query results:\n{json.dumps(results, indent=2, ensure_ascii=False)}")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to query embedding: {e}")

    @staticmethod
    def multi_delete_embedding(collection_name: str, ids: list[str]):
        """
        서버에서 ID 리스트의 데이터를 삭제하는 함수
        """
        url = f"{BASE_URL}/multiDelete"
        payload = {
            "collection_name": collection_name,
            "ids": ids
        }

        try:
            response = requests.delete(url, json=payload)
            response.raise_for_status()
            print(f"[SUCCESS] Embedding deleted: {response.json()}")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to delete embedding: {e}")

    @staticmethod
    def delete_embedding(collection_name: str, item_id: str):
        """
        서버에서 특정 ID의 데이터를 삭제하는 함수
        """
        url = f"{BASE_URL}/delete/{collection_name}/{item_id}"

        try:
            response = requests.delete(url)
            response.raise_for_status()
            print(f"[SUCCESS] Embedding deleted: {response.json()}")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to delete embedding: {e}")