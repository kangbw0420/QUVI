import json
import httpx
from typing import List, Dict, Optional
from dotenv import load_dotenv

from utils.config import Config

load_dotenv()

class FewShotRetriever:
    def __init__(self):
        self.base_url = Config.VECTOR_STORE_DOMAIN
        self.collections = {
            "analyzer": "question_analyzer",
            "executor": "result_executor",
            "respondent": "sql_respondent"
        }

    async def get_collection_name(self, task_type: str, collection_name: Optional[str] = None) -> str:
        """작업 유형과 collection_name을 기반으로 적절한 컬렉션 이름을 결정합니다.
        Returns:
            str: 사용할 컬렉션 이름.
        Raises:
            ValueError: task_type이 유효하지 않은 경우.
        """
        return collection_name

    async def query_vector_store(self, query_text: str, collection_name: str, top_k: int = 9) -> List[Dict]:
        """벡터 스토어에 쿼리를 보내 유사한 예제들을 검색합니다.
        Returns:
            List[Dict]: 검색된 문서와 메타데이터를 포함하는 결과 리스트.
            빈 리스트는 결과를 찾지 못했거나 에러가 발생한 경우를 의미.
        Raises:
            httpx.RequestError: API 요청 중 네트워크 오류 발생시.
            ValueError: API 응답이 예상된 형식이 아닌 경우.
        """
        async with httpx.AsyncClient() as client:
            try:
                request_payload = {
                    'collection_name': collection_name,
                    'query_text': query_text,
                    'top_k': top_k
                }
                print("\nRequest payload:", json.dumps(request_payload, ensure_ascii=False, indent=2))
                
                response = await client.post(
                    f"{self.base_url}/query",
                    json=request_payload
                )
                                
                response.raise_for_status()
                data = response.json()
                
                formatted_results = []
                if isinstance(data, dict) and "results" in data:
                    results = data["results"]
                    if "documents" in results and "metadatas" in results:
                        documents = results["documents"][0]  # First list contains documents
                        metadatas = results["metadatas"][0]  # First list contains metadatas
                        
                        # Pair documents with their metadata
                        for doc, meta in zip(documents, metadatas):
                            formatted_results.append({
                                "document": doc,
                                "metadata": meta
                            })
                        
                        return formatted_results
                
                print("Warning: Unexpected response format")
                return []
                
            except Exception as e:
                print(f"Error in query_vector_store: {str(e)}")
                return []

    async def format_few_shots(self, results: List[Dict]) -> List[Dict]:
        """벡터 스토어 검색 결과를 few-shot 예제 형식으로 변환합니다.
        Returns:
            List[Dict]: 입력(input)과 출력(output)을 포함하는 few-shot 예제 리스트.
            빈 리스트는 변환할 결과가 없거나 변환 중 오류가 발생한 경우를 의미.
        Raises:
            KeyError: 필요한 필드가 results에 없는 경우.
        """
        few_shots = []
        
        try:            
            for result in results:
                if "document" in result:
                    document = result["document"]
                    # Extract the question from document
                    question = document.strip()
                    
                    # Find corresponding metadata with SQL
                    metadata = result.get("metadata", {})
                    answer = metadata.get("answer", "")
                    if question and answer:
                        few_shot = {
                            "input": question,
                            "output": answer
                        }
                        few_shots.append(few_shot)            
            return few_shots
                
        except Exception as e:
            print(f"Error formatting few-shots: {str(e)}")
            return []

    async def get_few_shots(self, query_text: str, task_type: str, collection_name: Optional[str] = None) -> List[Dict]:
        """주어진 쿼리에 대한 few-shot 예제들을 검색합니다.
        
        Returns:
            List[Dict]: 검색된 few-shot 예제 리스트.
            빈 리스트는 예제를 찾지 못했거나 처리 중 오류가 발생한 경우를 의미.
        Raises:
            ValueError: task_type이 유효하지 않거나 컬렉션을 찾을 수 없는 경우.
            httpx.RequestError: 벡터 스토어 API 통신 중 오류 발생시.
        """
        collection_name = await self.get_collection_name(task_type, collection_name)
        if not collection_name:
            raise ValueError(f"Invalid task type: {task_type}")

        results = await self.query_vector_store(query_text, collection_name)
        few_shots = await self.format_few_shots(results)
        
        return few_shots

# Create a singleton instance
retriever = FewShotRetriever()