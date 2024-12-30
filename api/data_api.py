import json

from fastapi import APIRouter, HTTPException
from database.database_service import DatabaseService
from data_class.request import PostgreToVectorData, VectorDataQuery, PromptInput
data_api = APIRouter(tags=["data"])
data_service = DatabaseService()

@data_api.post("/upload")
def add_few_shot(data: PostgreToVectorData):
    """
    새 벡터 데이터를 추가하고 임베딩 시스템에 업데이트합니다.
    """
    try:
        success = data_service.add_few_shot(data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to insert vector data")
        return {"message": "Few-shot data added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Few-shot 데이터 업데이트
@data_api.put("/update")
def update_few_shot(data: PostgreToVectorData):
    """
    벡터 데이터를 업데이트하고 임베딩 시스템을 수정합니다.
    """
    try:
        success = data_service.update_few_shot(data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update vector data")
        return {"message": "Few-shot data updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Few-shot 데이터 삭제
@data_api.delete("/delete")
def delete_few_shot(data: PostgreToVectorData):
    """
    벡터 데이터를 삭제하고 임베딩 시스템에서 제거합니다.
    """
    try:
        success = data_service.delete_few_shot(data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete vector data")
        return {"message": "Few-shot data deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# PostgreSQL에서 Few-shot 데이터 조회
@data_api.post("/get/postgresql")
def get_postgre_few_shot(data: PostgreToVectorData):
    """
    PostgreSQL에서 Few-shot 데이터를 조회합니다.
    """
    try:
        result = data_service.get_postgre_few_shot(data)
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Prompt 데이터 추가
@data_api.post("/prompt/add")
def add_prompt(prompt: PromptInput):
    """
    새 Prompt를 추가합니다.
    """
    try:
        success = data_service.add_prompt(prompt.prompt_name, prompt.prompt)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to insert prompt data")
        return {"message": "Prompt added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Prompt 데이터 조회
@data_api.get("/prompt/get/{prompt_name}")
def get_prompt(prompt_name: str):
    """
    지정된 이름의 Prompt 데이터를 조회합니다.
    """
    try:
        result = data_service.get_prompt(prompt_name)
        if not result:
            raise HTTPException(status_code=404, detail="Prompt not found")
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))