import os

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException

from api.dto import VocRequest
from database.database_service import DatabaseService

voc_api = APIRouter(tags=["voc"])


# VOC 데이터 전체 조회
@voc_api.get("/getAll")
@voc_api.post("/getAll")
def get_all_voc():
    """
    VOC 데이터를 전체 조회합니다.
    """
    try:
        result = DatabaseService.get_all_voc()

        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# VOC 데이터 조회
@voc_api.get("/get")
def get_voc(data: VocRequest):
    """
    VOC 데이터를 전체 조회합니다.
    """
    try:
        result = DatabaseService.get_voc(data.seq)

        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# VOC 데이터 추가
@voc_api.post("/add")
def add_voc(data: VocRequest):
    """
    VOC 데이터를 추가합니다.
    """
    try:
        seq = DatabaseService.insert_voc(data)
        if not seq:
            raise HTTPException(status_code=500, detail="Failed to insert voc data")

        try:
            load_dotenv()
            ADMIN_DOMAIN = os.getenv("ADMIN_DOMAIN")

            llmURL = f"{ADMIN_DOMAIN}/main/llmadmin/{data.userId}"
            if (data.conversationId):
                llmURL += f"/conversation/{data.conversationId}"
            if (data.chainId):
                llmURL += f"/chain/{data.chainId}"

            apiURL = "https://api.flow.team/v1/posts/projects/2396558/tasks"

            contents = (f"인입경로 : {data.channel}\n"
                        f"아이디 : {data.userId}\n"
                        f"발화내용 : {data.utteranceContents}\n"
                        f"LLM로그 : {llmURL}\n"
                        f"문의내용 : {data.content}")
            # print(f"contents : {contents}")
            body = {
                "registerId": "philoyyj@daquv.com",
                "title": data.companyId,
                "contents": contents,
                "status": "request"
            }
            print(f"body : {body}")

            headers = {
                "Content-Type": "application/json",
                "x-flow-api-key": "20240903104057549-a1b44794-1dc5-42e4-9098-36939ab89144"
            }
            # print(f"headers : {headers}")

            response = requests.post(apiURL, json=body, headers=headers)
            response.raise_for_status()
            print(f"[FLOW] {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"[FLOW] Failed to post flow task: {e}")

        return {
            "status": 200,
            "success": True,
            "message": "Voc data inserted successfully",
            "body": {
                "seq": str(seq)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# VOC 데이터 수정
@voc_api.put("/update")
@voc_api.post("/update")
def update_voc(data: VocRequest):
    """
    VOC 데이터를 수정합니다.
    """
    try:
        success = DatabaseService.update_voc(data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update voc data")

        return {
            "status": 200,
            "success": True,
            "message": "Voc data updated successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# VOC 데이터 삭제
@voc_api.delete("/delete")
@voc_api.post("/delete")
def delete_voc(data: VocRequest):
    """
    VOC 데이터를 삭제합니다.
    """
    try:
        success = DatabaseService.delete_voc(data.seq)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete voc data")

        return {
            "status": 200,
            "success": True,
            "message": "Voc data deleted successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# VOC 데이터 삭제
@voc_api.post("/answer")
def answer_voc(data: VocRequest):
    """
    VOC 의 답변을 저장합니다.
    """
    try:
        success = DatabaseService.answer_voc(data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update voc answer data")

        return {
            "status": 200,
            "success": True,
            "message": "Voc Answer data updated successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@voc_api.post("/answer2")
def answer_voc2(data: VocRequest):
    """
    VOC 의 답변을 저장합니다.
    """
    try:
        success = DatabaseService.answer_voc(data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update voc answer data")

        try:
            DAQUV_API_DOMAIN = "https://aicfo-new.daquv.com"

            tokenData = {
                "userId": data.userId,
                "companyId": data.companyId
            }
            response = requests.post(DAQUV_API_DOMAIN + "/api/v1/auth/generate-token", json=tokenData)
            response.raise_for_status()
            print(f"[FLOW] {response.text()}")

            llmURL = f"https://{request.url.hostname}/main/llmadmin/{data.userId}"
            if (data.conversationId):
                llmURL += f"/conversation/{data.conversationId}"
            if (data.chainId):
                llmURL += f"/chain/{data.chainId}"
            print(f"llmURL : {llmURL}")

            contents = (f"인입경로 : {data.channel}\n"
                        f"아이디 : {data.userId}\n"
                        f"발화내용 : {data.utteranceContents}\n"
                        f"LLM로그 : {llmURL}\n"
                        f"문의내용 : {data.content}")
            print(f"contents : {contents}")
            apiURL = "https://api.flow.team/v1/posts/projects/2396558/tasks"
            print(f"apiURL : {apiURL}")
            body = {
                "registerId": "philoyyj@daquv.com",
                "title": data.companyId,
                "contents": contents,
                "status": "request"
            }
            print(f"body : {body}")
            headers = {
                "Content-Type": "application/json",
                "x-flow-api-key": "20240903104057549-a1b44794-1dc5-42e4-9098-36939ab89144"
            }
            print(f"headers : {headers}")

            response = requests.post(apiURL, json=body, headers=headers)
            response.raise_for_status()
            print(f"[FLOW] {response.text()}")

        except requests.exceptions.RequestException as e:
            print(f"[FLOW] Failed to post flow task: {e}")

        return {
            "status": 200,
            "success": True,
            "message": "Voc Answer data updated successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))