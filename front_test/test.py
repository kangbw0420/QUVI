import requests
import json
import time

def test_korean_questions():
    # 테스트할 한글 질문들
    questions = [
        "2024년 웹케시 월간 거래내역 정리해줘"
    ]
    temp = ""
    for question in questions:
        print(f"\n테스트 질문: {question}")

        payload = {
            "user_question": question,
            "user_id": "default_user",
            "last_question":"",
            "last_answer":"",
            "last_sql_query":"",
            "session_id": "default_session"
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
        # 테스트할 한글 질문들
    
    questions = [
        "오늘은 어때?"
    ]
    temp = json.loads(json.dumps(response.json(), ensure_ascii=False, indent=2))

    for question in questions:
        print(f"\n테스트 질문: {question}")
        try:
            payload = {
                "user_question": question,
                "user_id": "default_user",
                "last_question": temp.get("body").get("result").get("question"),
                "last_answer": temp.get("body").get("result").get("answer"),
                "last_sql_query": temp.get("body").get("SQL"),
                
            }
        except Exception as E:
            print("Before process fails.")
            payload = {
                "user_question": question,
                "user_id": "default_user",
                "session_id": "default_session"
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