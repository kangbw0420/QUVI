import requests
import json
import time

def test_korean_questions():
    # 테스트할 한글 질문들
    questions = [
        "1월 5일에 잔액 얼마야"
    ]

    for question in questions:
        print(f"\n테스트 질문: {question}")

        payload = {
            "user_question": question,
            "user_id": "default_user",
            "session_id": "DEV_SESSION_ID",# DEV_SESSION_ID=꼬리물기 및 DB저장 X,  f0e89beb-eac9-4d8e-bff9-79a83f1b2b5a
        }

        try:
            response = requests.post(
                "http://localhost:8000/process",
                headers={"Content-Type": "application/json; charset=utf-8"},
                json=payload
            )
            
            # 응답 결과를 JSON 문자열로 변환
            response_str = json.dumps(response.json(), ensure_ascii=False, indent=2)
            # 1000자로 제한하고 잘렸다는 것을 표시
            if len(response_str) > 1000:
                print("응답 결과:", response_str[:1000] + "...")
            else:
                print("응답 결과:", response_str)
            
        except Exception as e:
            print("오류 발생:", str(e))

        time.sleep(2)  # 요청 간 간격

if __name__ == "__main__":
    test_korean_questions()