from datetime import datetime

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException

from api.dto import VocRequest
from database.database_service import DatabaseService
from utils.config import Config

voc_api = APIRouter(tags=["voc"])


# VOC 데이터 전체 조회
@voc_api.post("/getAll")
@voc_api.get("/getAll")
def get_all_voc():
    """
    VOC 데이터를 전체 조회합니다.
    """
    try:
        result = DatabaseService.get_all_voc()

        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# VOC 데이터 단건 조회
@voc_api.get("/get/{seq}")
def get_voc(seq: int):
    """
    VOC 데이터를 단건 조회합니다.
    """
    try:
        result = DatabaseService.get_voc(seq)
        if result:
            result = result[0]

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

        response = flow_post_task(data)
        print(f"[FLOW] response : {response.text}")

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
@voc_api.post("/update")
# @voc_api.put("/update")
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
@voc_api.post("/delete")
# @voc_api.delete("/delete")
def delete_voc(data: VocRequest):
# @voc_api.delete("/delete/{seq}")
# def delete_voc(seq: int):
    """
    VOC 데이터를 삭제합니다.
    """
    try:
        success = DatabaseService.delete_voc(data.seq)
        # success = DatabaseService.delete_voc(seq)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete voc data")

        return {
            "status": 200,
            "success": True,
            "message": "Voc data deleted successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# VOC 데이터 답변 업데이트
@voc_api.post("/answer")
def answer_voc(data: VocRequest):
    """
    VOC 의 답변을 저장합니다.
    """
    try:
        success = DatabaseService.answer_voc(data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update voc answer data")

        response = push_answer(data)
        print(f"[PUSH] response : {response.text}")

        return {
            "status": 200,
            "success": True,
            "message": "Voc Answer data updated successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




def flow_post_task(data: VocRequest):
    ADMIN_DOMAIN = Config.ADMIN_DOMAIN

    try:
        apiURL = "https://api.flow.team/v1/posts/projects/2396558/tasks"

        llmURL = ""
        if data.utteranceContents:
            if (data.conversationId):
                llmURL += f"/conversation/{data.conversationId}"
            if (data.chainId):
                llmURL += f"/chain/{data.chainId}"
            if llmURL:
                llmURL = f"{ADMIN_DOMAIN}/main/llmadmin/{data.userId}" + llmURL

        title = (f"[{data.companyId}] {data.utteranceContents}")
        contents = (f"인입경로 : {data.channel}\n"
                    f"아이디 : {data.userId}\n"
                    f"발화내용 : {data.utteranceContents}\n"
                    f"LLM로그 : {llmURL}\n"
                    f"----------------------------------------------------------------------\n"
                    f"{data.content}")
        # print(f"[FLOW] contents : {contents}")

        body = {
            "registerId": "philoyyj@daquv.com",
            "title": title,
            "contents": contents,
            "status": "request"
        }
        print(f"[FLOW] body : {body}")

        headers = {
            "Content-Type": "application/json",
            "x-flow-api-key": "20240903104057549-a1b44794-1dc5-42e4-9098-36939ab89144"
        }
        # print(f"[FLOW] headers : {headers}")

        response = requests.post(apiURL, json=body, headers=headers)
        response.raise_for_status()

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def push_answer(data: VocRequest):
    DAQUV_API_DOMAIN = Config.DAQUV_API_DOMAIN

    try:
        result = DatabaseService.get_voc(data.seq)
        if result:
            result = result[0]
        # print(f"result : {result}")

        tokenData = {
            "userId": result['user_id'],
            # "companyId": result['company_id'],
            "companyId": result['use_intt_id'],
        }
        tokenResponse = requests.post(DAQUV_API_DOMAIN + "/api/v1/auth/generate-token", json=tokenData)
        tokenResponse.raise_for_status()
        tokenJson = tokenResponse.json()
        if tokenJson['success']:
            jwtToken = tokenJson['body']['JWT-TOKEN']
            # print(f"[PUSH] jwtToken : {jwtToken}")

        now = datetime.now()
        formattedNow = now.strftime('%Y-%m-%d %H:%M:%S')
        # print(f"[PUSH] formattedNow : {formattedNow}")

        pushData = {
            "pushTitle": "문의하신 내용에 대한 답변이 도착했습니다.",
            "pushBody": result['answer'],
            "bodyTitle": "",
            "bodyText1": "문의하신 내용에 대한 답변이 도착했습니다.",
            "bodyText2": result['answer'],
            "bodyText3": "",
            "bodyText4": formattedNow,
            "vocSeq": result['seq'],
            "userId": result['user_id'],
            "useInttId": result['use_intt_id'],
        }
        print(f"[PUSH] pushData : {pushData}")

        headers = {
            "Content-Type": "application/json",
            "Authorization": jwtToken
        }
        # print(f"[PUSH] headers : {headers}")

        pushResponse = requests.post(DAQUV_API_DOMAIN + "/api/v1/push/voc", json=pushData, headers=headers)
        pushResponse.raise_for_status()

        return pushResponse
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))