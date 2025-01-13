import requests
import json
import time

def test_korean_questions():
    # 테스트할 한글 질문들
    questions = [
        "잔액이 많은 상위 5개 계좌를  보여줘.",
        "현재 잔액을 보여줘.",
        "거래내역을 보여줘.",
        "10억 이상 되는 계좌를 보여줘.",
        "그 계좌의 거래내역 보여줘.",
        "123계좌 오늘자 잔액을 보여줘.",
        "거래내역을 보여줘."
    ]
    for question in questions:
        print(f"\n테스트 질문: {question}")

        payload = {
            "user_question": question,
            "user_id": "default_user",
            "session_id": "f0e89beb-eac9-4d8e-bff9-79a83f1b2b5a",# f0e89beb-eac9-4d8e-bff9-79a83f1b2b5a
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