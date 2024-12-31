import asyncio
from prompts.retriever import FewShotRetriever
from typing import Dict, List
import json

async def test_get_collection_name():
    retriever = FewShotRetriever()
    
    # Test cases
    test_cases = [
        {
            "task_type": "analyzer",
            "collection_name": "shots_2011",
            "expected": "question_analyzer"
        },
        {
            "task_type": "creator",
            "collection_name": "shots_2011",
            "expected": "shot_2011"
        },
        {
            "task_type": "respondent",
            "collection_name": "shots_2011",
            "expected": "sql_respondent"
        }
    ]
    
    print("\nTesting get_collection_name:")
    for case in test_cases:
        result = await retriever.get_collection_name(case["task_type"], case["collection_name"])
        success = result == case["expected"]
        print(f"Task: {case['task_type']}, Collection: {case['collection_name']}")
        print(f"Expected: {case['expected']}, Got: {result}")
        print(f"Test {'passed' if success else 'failed'}\n")

async def test_get_few_shots():
    retriever = FewShotRetriever()
    
    # Test cases
    test_cases = [
        {
            "query_text": "24년 급여내역 정리해줘",
            "task_type": "analyzer",
            "collection_name": "shots_2011"
        },
        {
            "query_text": "24년 급여내역 정리해줘",
            "task_type": "creator",
            "collection_name": "shots_2011"
        }
    ]
    
    print("\nTesting get_few_shots:")
    for case in test_cases:
        print(f"\n{'='*50}")
        print(f"Testing case:")
        print(f"Task type: {case['task_type']}")
        print(f"Query text: {case['query_text']}")
        print(f"Collection name: {case['collection_name']}")
        
        try:
            # First test get_collection_name
            collection_name = await retriever.get_collection_name(
                case["task_type"],
                case["collection_name"]
            )
            print(f"\nCollection name resolved to: {collection_name}")
            
            # Then get few shots
            results = await retriever.get_few_shots(
                case["query_text"],
                case["task_type"],
                case["collection_name"]
            )
            
            print(f"\nResults retrieved: {len(results)}")
            if results:
                print("\nResults structure:")
                print(json.dumps(results, indent=2, ensure_ascii=False))
                
                print("\nValidating results:")
                for idx, example in enumerate(results):
                    print(f"\nExample {idx + 1}:")
                    print(f"Keys present: {list(example.keys())}")
                    print(f"Input length: {len(str(example.get('input', '')))}")
                    print(f"Output length: {len(str(example.get('output', '')))}")
            else:
                print("\nNo results returned")
                    
        except Exception as e:
            print(f"\nError occurred: {str(e)}")
            import traceback
            print(f"Traceback:\n{traceback.format_exc()}")

async def main():
    print("Starting FewShotRetriever tests...")
    
    # Run all tests
    await test_get_collection_name()
    await test_get_few_shots()
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(main())