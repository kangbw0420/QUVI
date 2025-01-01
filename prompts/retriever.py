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
            List of dictionaries containing query results
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
                
                print(f"Response status: {response.status_code}")
                print(f"Response content preview: {response.text[:500]}...")
                
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
                        
                        print(f"\nFormatted {len(formatted_results)} results")
                        return formatted_results
                
                print("Warning: Unexpected response format")
                return []
                
            except Exception as e:
                print(f"Error in query_vector_store: {str(e)}")
                return []

    async def format_few_shots(self, results: List[Dict]) -> List[Dict]:
        """
        Format vector store results into few-shot examples.
        
        Args:
            results: List of dictionaries containing query results
                
        Returns:
            List of formatted few-shot examples with input (question) and output (SQL)
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
                    sql = metadata.get("SQL", "")
                    
                    if question and sql:
                        few_shot = {
                            "input": question,
                            "output": sql
                        }
                        few_shots.append(few_shot)
                        print(f"\nProcessed few-shot example:")
                        print(f"Question: {few_shot['input']}")
                        print(f"SQL: {few_shot['output']}")
            
            return few_shots
                
        except Exception as e:
            print(f"Error formatting few-shots: {str(e)}")
            print(f"Input results structure: {results}")
            return []

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