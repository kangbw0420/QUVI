import os
import json
import uuid
import requests

FILENAME = "shots_api_selector.json"  # 🔧 파일 이름만 바꿔서 실행
FILEPATH = os.path.join("shots", FILENAME)

CHROMA_URL = "http://183.102.124.135:8001/add"
HEADERS = {"Content-Type": "application/json"}

collection_name = os.path.splitext(FILENAME)[0]
BATCH_SIZE = 100

if not os.path.exists(FILEPATH):
    print(f"❌ 파일을 찾을 수 없습니다: {FILEPATH}")
    exit()

try:
    with open(FILEPATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents = []
    for item in data:
        if "question" in item and "answer" in item:
            question = item["question"].strip()
            answer = item["answer"].strip()
            date = item.get("date", "").strip()

            # ✅ date가 있을 경우 질문에 포함
            if date:
                doc_str = f"질문: {question}, 오늘: {date}\n답변: {answer}"
            else:
                doc_str = f"질문: {question}\n답변: {answer}"

            documents.append(doc_str)

    print(f"📄 총 문서 수: {len(documents)}")

    for i in range(0, len(documents), BATCH_SIZE):
        batch_docs = documents[i:i+BATCH_SIZE]
        payload = {
            "collection_name": collection_name,
            "documents": batch_docs,
            "metadatas": [{"source": collection_name} for _ in batch_docs],
            "ids": [str(uuid.uuid4()) for _ in batch_docs]
        }

        response = requests.post(CHROMA_URL, headers=HEADERS, json=payload)
        print(f"📦 {i} ~ {i + len(batch_docs) - 1} 업로드 완료 - 상태: {response.status_code}")
        try:
            print("서버 응답:", response.json())
        except Exception:
            print("응답 텍스트:", response.text)

except Exception as e:
    print(f"❌ 처리 중 오류 발생: {e}")
