import requests
import json
import time

def test_korean_questions():
    # 테스트할 한글 질문들
    questions = [
        "신한은행 계좌에 얼마 있어?"
    ]

    for question in questions:
        print(f"\n테스트 질문: {question}")

        payload = {
            "user_question": question,
            "user_id": "default_user"
        }

        try:
            response = requests.post(
                "http://localhost:8000/process",
                headers={"Content-Type": "application/json; charset=utf-8"},
                json=payload
            )
            
            print("상태 코드:", response.status_code)
            print("응답 결과:", json.dumps(response.json(), ensure_ascii=False, indent=2))
            
        except Exception as e:
            print("오류 발생:", str(e))

        time.sleep(2)  # 요청 간 간격

if __name__ == "__main__":
    test_korean_questions()