import json

import requests

from utils.config import Config


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
            print(f"[SUCCESS] Query results:\n{json.dumps(results, indent=2, ensure_ascii=False)}")

            return results
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to query embedding: {e}")


    def get_embedding(collection_name: str):
        """
        서버에서 데이터를 조회하는 함수
        """
        url = f"{BASE_URL}/get/{collection_name}"

        try:
            response = requests.get(url)
            response.raise_for_status()

            results = response.json()
            print(f"[SUCCESS] Get Embedding results:\n{json.dumps(results, indent=2, ensure_ascii=False)}")

            return results
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to test embedding: {e}")


    def getAll_embedding():
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
            print(f"[ERROR] Failed to getAll embedding: {e}")


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

            print(f"[SUCCESS] {collection_name} / Embedding added: {response.json()}")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] {collection_name} / Failed to add embedding: {e}")


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


    def collection_delete_embedding(collection_name: str):
        """
        서버에서 ID 리스트의 데이터를 삭제하는 함수
        """
        # url = f"{BASE_URL}/multiDelete"
        url = f"{BASE_URL}/collectionDelete"
        payload = {
            "collection_name": collection_name,
        }

        try:
            response = requests.delete(url, json=payload)
            response.raise_for_status()

            print(f"[SUCCESS] Embedding collection deleted: {response.json()}")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to collection delete embedding: {e}")