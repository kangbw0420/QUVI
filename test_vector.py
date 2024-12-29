from dotenv import load_dotenv
import logging
import json
import requests
from utils.config import Config
from database.vector_db import EmbeddingAPIClient

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

def analyze_vector_db_contents():
    """
    Vector DB의 내용을 분석하고 출력합니다.
    모든 테스트가 성공적으로 완료되었을 때만 True를 반환합니다.
    """
    all_tests_passed = True  # 모든 테스트 성공 여부 추적

    try:
        # API URL 확인
        base_url = Config.VECTOR_STORE_DOMAIN
        logger.info(f"Using API URL: {base_url}")
        
        # 1. 컬렉션 목록 조회 테스트
        logger.info("\n=== Collections Test ===")
        collections_url = f"{base_url}/collections"
        try:
            response = requests.get(collections_url)
            if response.status_code == 200:
                collections = response.json()
                logger.info(f"Available collections: {json.dumps(collections, indent=2, ensure_ascii=False)}")
            else:
                logger.error(f"Failed to get collections. Status code: {response.status_code}")
                all_tests_passed = False
        except Exception as e:
            logger.error(f"Error getting collections: {str(e)}")
            all_tests_passed = False

        # 2. 각 컬렉션에 대한 쿼리 테스트
        logger.info("\n=== Query Test ===")
        test_collections = ["test_collection"]  # 테스트할 컬렉션 목록
        
        for collection_name in test_collections:
            logger.info(f"\nTesting collection: {collection_name}")
            
            test_params = {
                "collection_name": collection_name,
                "query_text": "테스트 쿼리",
                "top_k": 5
            }
            
            try:
                logger.info("Executing query with parameters:")
                logger.info(json.dumps(test_params, indent=2, ensure_ascii=False))
                
                # 쿼리 실행 및 응답 캡처
                url = f"{base_url}/query"
                response = requests.post(url, json=test_params)
                
                if response.status_code == 200:
                    results = response.json()
                    logger.info("\nQuery Results:")
                    logger.info(json.dumps(results, indent=2, ensure_ascii=False))
                    
                    # 결과 분석
                    if results and isinstance(results, list):
                        logger.info(f"\nFound {len(results)} matches:")
                        for idx, match in enumerate(results, 1):
                            logger.info(f"\nMatch {idx}:")
                            logger.info(f"ID: {match.get('id', 'N/A')}")
                            logger.info(f"Text: {match.get('text', 'N/A')}")
                            logger.info(f"Score: {match.get('score', 'N/A')}")
                    else:
                        logger.warning("No results found or invalid response format")
                        all_tests_passed = False
                else:
                    logger.error(f"Query failed with status code: {response.status_code}")
                    logger.error(f"Response: {response.text}")
                    all_tests_passed = False
                
            except Exception as e:
                logger.error(f"Error during query test: {str(e)}")
                all_tests_passed = False
        
        return all_tests_passed
            
    except Exception as e:
        logger.error(f"Test setup failed: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting Vector DB analysis...")
    success = analyze_vector_db_contents()
    
    if success:
        logger.info("\n✅ Analysis completed successfully")
    else:
        logger.error("\n❌ Analysis failed")
        exit(1)  # 실패 시 non-zero exit code 반환