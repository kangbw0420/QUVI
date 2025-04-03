import time
import json
import httpx
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv
import requests

from utils.config import Config
from utils.logger import setup_logger

load_dotenv()

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

                response = await client.post(
                    f"{self.base_url}/query",
                    json=request_payload
                )

                process_time = (time.time() - start_time) * 1000
                logger.info(f"Vector store query completed in {process_time:.2f}ms")

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

                logger.warning("Unexpected response format from vector store")
                return []

            except Exception as e:
                logger.error(f"Error in query_vector_store: {str(e)}")
                return []

    async def format_few_shots(self, results: List[Dict]) -> List[Dict]:
        """벡터 스토어 검색 결과를 few-shot 예제 형식으로 변환합니다."""
        few_shots = []

        try:
            for result in results:
                if "document" in result:
                    document = result["document"].strip()

                    # ✅ "결과 데이터:" 블럭 분리
                    stats_block = ""
                    if "결과 데이터:" in document:
                        doc_parts = document.split("질문:")
                        if len(doc_parts) >= 2:
                            stats_block = doc_parts[0].replace("결과 데이터:", "").strip()
                            remaining = "질문:" + doc_parts[1]
                        else:
                            remaining = document
                    else:
                        remaining = document

                    # ✅ "질문: ...\n답변: ..." 분리
                    question, answer = "", ""
                    lines = remaining.split("\n")
                    for line in lines:
                        if line.startswith("질문:"):
                            question = line.replace("질문:", "").strip()
                        elif line.startswith("답변:"):
                            answer = line.replace("답변:", "").strip()

                    if question and answer:
                        few_shot = {
                            "input": question,
                            "output": answer
                        }

                        # ✅ stats는 document에서 추출한 경우 우선 사용
                        if stats_block:
                            few_shot["stats"] = stats_block

                        # ✅ 추가 metadata가 있으면 넣음
                        metadata = result.get("metadata", {})
                        if "date" in metadata:
                            few_shot["date"] = metadata["date"]
                        if "stats" in metadata and "stats" not in few_shot:
                            few_shot["stats"] = metadata["stats"]

                        few_shots.append(few_shot)

            return few_shots

        except Exception as e:
            logger.error(f"❌ Error formatting few-shots: {str(e)}")
            return []

    async def get_few_shots(self, query_text: str, collection_name: Optional[str] = None, top_k: int = 6) -> List[Dict]:
        """주어진 쿼리에 대한 few-shot 예제들을 검색합니다.
        Returns:
            List[Dict]: 검색된 few-shot 예제 리스트.
            빈 리스트는 예제를 찾지 못했거나 처리 중 오류가 발생한 경우를 의미.
        Raises:
            httpx.RequestError: 벡터 스토어 API 통신 중 오류 발생시.
        """
        results = await self.query_vector_store(query_text, collection_name, top_k=top_k)

        if logger.isEnabledFor(10):  # DEBUG level
            logger.debug(f"Vector store results: {results}")

        few_shots = await self.format_few_shots(results)

        return few_shots

    async def get_recommend(self, query_text: str, top_k: int = 4) -> List[Dict]:
        """벡터 DB에서 유사한 질문 4개를 검색하고, 조건에 따라 3개를 반환합니다.
        Returns:
            List[str]: 검색된 문서 중 선별된 3개의 문서 리스트.
            - 입력된 query_text와 동일한 문서가 있는 경우: 해당 문서를 제외한 3개
            - 입력된 query_text와 동일한 문서가 없는 경우: 마지막 문서를 제외한 3개
        """
        # 벡터 DB에서 4개 검색
        results = await self.query_vector_store(query_text, collection_name="hall_of_fame", top_k=top_k)

        # document 추출 및 strip() 적용, 띄어쓰기 제거
        query_text_normalized = query_text.replace(" ", "").strip()
        documents = [result["document"].strip() for result in results if "document" in result]
        documents_normalized = [doc.replace(" ", "") for doc in documents]

        if not documents:
            return []

        # query_text가 검색 결과에 있는지 확인
        try:
            query_index = documents_normalized.index(query_text_normalized)
            # query_text가 있으면 해당 항목을 제외한 나머지 중 앞의 3개 반환
            filtered_docs = documents[:query_index] + documents[query_index + 1:]
            return filtered_docs[:3]
        except ValueError:
            # query_text가 없으면 마지막 항목을 제외한 3개 반환
            return documents[:3]
    
    async def get_evernote(self, note_str: str, available_notes: List[str], top_k: int = 10, threshold: float = 0.5) -> List[str]:
        try:
            if not available_notes:
                logger.warning("No available notes provided to get_evernote")
                return []

            similar_notes = []

            request_payload = {
                'pickItems': [
                    {
                        'target': note_str,
                        'candidates': available_notes
                    }
                ],
                'top_k': top_k
            }
            
            logger.debug(f"Request payload for note similarity: {json.dumps(request_payload, ensure_ascii=False, indent=2)}")

            response = requests.post(
                f"{self.base_url}/pick",
                json=request_payload,
                timeout=10.0
            )

            response.raise_for_status()
            data = response.json()

            # Extract similar notes from response in the format described
            if isinstance(data, dict) and "results" in data:
                for result_item in data["results"]:
                    if isinstance(result_item, dict) and result_item.get("target") == note_str and "candidates" in result_item:
                        # The 'candidates' field contains a list of objects with 'candidate' and 'score' fields
                        for candidate_obj in result_item["candidates"]:
                            if isinstance(candidate_obj, dict) and "candidate" in candidate_obj and "score" in candidate_obj:
                                candidate = candidate_obj["candidate"]
                                score = candidate_obj["score"]

                                if score >= threshold and candidate not in similar_notes:
                                    similar_notes.append(candidate)
                                    logger.debug(f"Found similar note: '{candidate}' with score {score}")

            logger.info(f"Found {len(similar_notes)} similar notes above threshold {threshold}")

            return similar_notes

        except Exception as e:
            logger.error(f"Error in get_evernote: {e}")
            return []
        
def api_recommend(selected_api: str):
    # 자금현황
    if selected_api == 'aicfo_get_financial_status':
        recommendations = ['수시 잔액 상세', '예적금 잔액 상세', '대출 잔액 상세']
    # 자금변동현황
    elif selected_api == 'aicfo_get_variation_status':
        recommendations = ['어제 수시입출 계좌 거래내역', '어제 예적금 계좌 거래내역', '어제 외화계좌 거래내역']
    # 월간자금흐름
    elif selected_api == 'aicfo_get_monthly_flow':
        recommendations = ['2개월 전 자금 흐름', '지난 달 수시입출계좌 출금만 보여줘', '증권 계좌 수익률']
    # 가용자금
    if selected_api == 'aicfo_get_available_fund':
        return ['수시 잔액 상세', '외화 잔액 상세', '달러 잔액 상세']

# Create a singleton instance
retriever = FewShotRetriever()