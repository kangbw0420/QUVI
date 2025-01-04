import requests
import json
import time
from typing import Dict, Any


def send_request(endpoint: str, question: str, user_id: str = "default_user") -> Dict[str, Any]:
    """지정된 엔드포인트로 요청을 보내는 함수"""
    url = f"http://localhost:8000/{endpoint}"
    payload = {
        "user_question": question,
        "user_id": user_id
    }
    
    response = requests.post(
        url,
        headers={"Content-Type": "application/json; charset=utf-8"},
        json=payload
    )
    
    return response.json()

def print_response(endpoint: str, question: str, response: Dict[str, Any]):
    """응답 결과를 보기 좋게 출력하는 함수"""
    print(f"\n=== {endpoint.upper()} 테스트 ===")
    print(f"질문: {question}")
    print("\n응답:")
    
    # regression인 경우 출력 제한
    if endpoint == "regression":
        response_str = json.dumps(response, ensure_ascii=False, indent=2)
        if len(response_str) > 5000:
            print(response_str[:5000] + "...(이하 생략)")
        else:
            print(response_str)
    else:
        print(json.dumps(response, ensure_ascii=False, indent=2))
    
    print("="* 50)


def test_classification():
    """정기 거래 패턴 분석 엔드포인트 테스트"""
    questions = [
        "정기적인 지출 중에서 금액이 가장 큰 것은 어떤 계좌번호에서 얼마씩 나가나요?"
    ]
    
    print("\n=== 정기 거래 패턴 분석 테스트 시작 ===")
    for question in questions:
        try:
            response = send_request("classification", question)
            print_response("classification", question, response)
        except Exception as e:
            print(f"Classification 테스트 중 오류 발생: {str(e)}")
        time.sleep(2)


def test_regression():
    """미래 예측 분석 엔드포인트 테스트"""
    questions = [
        "2025년 말까지 예상되는 총 순수입은 얼마인가요?"
        ]
    
    print("\n=== 미래 예측 분석 테스트 시작 ===")
    for question in questions:
        try:
            response = send_request("regression", question)
            print_response("regression", question, response)
        except Exception as e:
            print(f"Regression 테스트 중 오류 발생: {str(e)}")
        time.sleep(2)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='API 엔드포인트 테스트')
    parser.add_argument('endpoint', choices=['classification', 'regression'], 
                       help='테스트할 엔드포인트 선택')
    
    args = parser.parse_args()
    
    try:
        if args.endpoint == 'classification':
            test_classification()
        else:
            test_regression()
    except KeyboardInterrupt:
        print("\n테스트가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n테스트 실행 중 오류가 발생했습니다: {str(e)}")
    finally:
        print("\n테스트가 완료되었습니다.")