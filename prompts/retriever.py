import re
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
        self.table_pattern = r"aicfo_get_cabo_\d{4}"

    async def get_collection_name(self, task_type: str, collection_name: Optional[str] = None) -> str:
        """
        Get the appropriate collection name based on task type and table name.
        
        Args:
            task_type: Type of task (analyzer, creator, executor, respondent)
            collection_name: Optional table name for query_creator
            
        Returns:
            Collection name to query
        """
        return collection_name

    async def query_vector_store(self, query_text: str, collection_name: str, top_k: int = 3) -> List[Dict]:
        """
        Query the vector store through the API endpoint.
        
        Args:
            query_text: Text to find similar examples for
            collection_name: Name of the collection to query
            top_k: Number of results to return
            
        Returns:
            List of similar examples
        """
        async with httpx.AsyncClient() as client:
            try:
                # Print request details for debugging
                print(f"\nMaking request to: {self.base_url}/query")
                request_payload = {
                    'collection_name': collection_name,
                    'query_text': query_text,
                    'top_k': top_k
                }
                print("Request payload:", json.dumps(request_payload, ensure_ascii=False, indent=2))
                
                response = await client.post(
                    f"{self.base_url}/query",
                    json={
                        "collection_name": collection_name,
                        "query_text": query_text,
                        "top_k": top_k
                    }
                )
                
                # Print response details for debugging
                print(f"Response status: {response.status_code}")
                print(f"Response content: {response.text[:500]}...")  # First 500 chars
                
                response.raise_for_status()
                
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        return data.get("results", [])
                    else:
                        print(f"Unexpected response format. Expected dict, got {type(data)}")
                        return []
                except json.JSONDecodeError as e:
                    print(f"Failed to decode JSON response: {str(e)}")
                    return []
                    
            except httpx.HTTPError as e:
                print(f"HTTP Error querying vector store: {str(e)}")
                return []
            except Exception as e:
                print(f"Unexpected error in query_vector_store: {str(e)}")
                return []

    async def format_few_shots(self, results: List[Dict]) -> List[Dict]:
        """
        Format vector store results into few-shot examples.
        
        Args:
            results: Raw results from vector store
            
        Returns:
            List of formatted few-shot examples
        """
        few_shots = []
        for result in results:
            try:
                # Parse the stored example data
                example_data = json.loads(result.get("document", "{}"))
                few_shot = {
                    "input": example_data.get("input", ""),
                    "output": example_data.get("output", "")
                }
                few_shots.append(few_shot)
            except json.JSONDecodeError:
                print(f"Error parsing example data: {result.get('document')}")
                continue
        return few_shots

    async def get_few_shots(self, query_text: str, task_type: str, collection_name: Optional[str] = None) -> List[Dict]:
        """
        Main method to get few-shot examples for a given query.
        
        Args:
            query_text: The query to find similar examples for
            task_type: Type of task (analyzer, creator, executor, respondent)
            collection_name: Optional table name for query_creator
            
        Returns:
            List of few-shot examples formatted for use in prompts
        """
        collection_name = await self.get_collection_name(task_type, collection_name)
        if not collection_name:
            raise ValueError(f"Invalid task type: {task_type}")

        results = await self.query_vector_store(query_text, collection_name)
        few_shots = await self.format_few_shots(results)
        
        return few_shots

# Create a singleton instance
retriever = FewShotRetriever()