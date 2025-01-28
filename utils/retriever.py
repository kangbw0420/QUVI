import time
import json
import httpx
from typing import List, Dict, Optional
from dotenv import load_dotenv

from utils.config import Config
from utils.logger import setup_logger

load_dotenv()

# 모듈별 로거 설정
logger = setup_logger('retriever')

class FewShotRetriever:
    def __init__(self):
        self.base_url = Config.VECTOR_STORE_DOMAIN

    async def query_vector_store(self, query_text: str, collection_name: str, top_k: int = 6) -> List[Dict]:
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

                start_time = time.time()
                logger.info(f"Starting vector store query for {collection_name}")
                logger.debug(f"Request payload: {json.dumps(request_payload, ensure_ascii=False, indent=2)}")
                                
                response = await client.post(
                    f"{self.base_url}/query",
                    json=request_payload
                )
                                
                process_time = (time.time() - start_time) * 1000
                logger.info(f"Completed vector store query for {collection_name} - {process_time:.2f}ms")
                                
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
                
                logger.warning("Unexpected response format")
                return []
                
            except Exception as e:
                logger.error(f"Error in query_vector_store: {str(e)}")
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
                        
                        # If metadata has date key, include it in few_shot
                        if "date" in metadata:
                            date = metadata.get("date", "")
                            few_shot["date"] = date
                        
                        # If metadata has stats key, include it in few_shot
                        if "stats" in metadata:
                            stats = metadata.get("stats", "")
                            few_shot["stats"] = stats
                            
                        few_shots.append(few_shot)            
                    
                return few_shots
                    
        except Exception as e:
            logger.error(f"Error formatting few-shots: {str(e)}")
            return []

    async def get_few_shots(self, query_text: str, collection_name: Optional[str] = None, top_k: int=6) -> List[Dict]:
        """주어진 쿼리에 대한 few-shot 예제들을 검색합니다.
        Returns:
            List[Dict]: 검색된 few-shot 예제 리스트.
            빈 리스트는 예제를 찾지 못했거나 처리 중 오류가 발생한 경우를 의미.
        Raises:
            httpx.RequestError: 벡터 스토어 API 통신 중 오류 발생시.
        """
        results = await self.query_vector_store(query_text, collection_name, top_k=top_k)
        logger.debug(f"Vector store results: {results}")
        few_shots = await self.format_few_shots(results)
        
        return few_shots

# Create a singleton instance
retriever = FewShotRetriever()
