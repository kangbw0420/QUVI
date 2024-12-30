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

    async def get_collection_name(self, task_type: str, table_name: Optional[str] = None) -> str:
        """
        Get the appropriate collection name based on task type and table name.
        
        Args:
            task_type: Type of task (analyzer, creator, executor, respondent)
            table_name: Optional table name for query_creator
            
        Returns:
            Collection name to query
        """
        if task_type == "creator" and table_name:
            # Extract the year part from table name and create collection name
            match = re.search(r"\d{4}", table_name)
            if match:
                year = match.group(0)
                return f"shot_{year}"
            raise ValueError(f"Invalid table name format: {table_name}")
        
        return self.collections.get(task_type, "")

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
                response = await client.post(
                    f"{self.base_url}/query",
                    json={
                        "collection_name": collection_name,
                        "query_text": query_text,
                        "top_k": top_k
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data.get("results", [])
            except httpx.HTTPError as e:
                print(f"Error querying vector store: {str(e)}")
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

    async def get_few_shots(self, query_text: str, task_type: str, table_name: Optional[str] = None) -> List[Dict]:
        """
        Main method to get few-shot examples for a given query.
        
        Args:
            query_text: The query to find similar examples for
            task_type: Type of task (analyzer, creator, executor, respondent)
            table_name: Optional table name for query_creator
            
        Returns:
            List of few-shot examples formatted for use in prompts
        """
        collection_name = await self.get_collection_name(task_type, table_name)
        if not collection_name:
            raise ValueError(f"Invalid task type: {task_type}")

        results = await self.query_vector_store(query_text, collection_name)
        few_shots = await self.format_few_shots(results)
        
        return few_shots

# Create a singleton instance
retriever = FewShotRetriever()