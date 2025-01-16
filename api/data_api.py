from fastapi import APIRouter, HTTPException

from data_class.request import PostgreToVectorData, PromptInput
from database.database_service import DatabaseService

data_api = APIRouter(tags=["data"])


@data_api.get("/test/{collection_name}")
def test_get_few_shot(collection_name: str):
    try:
        result = DatabaseService.test_get_few_shot(collection_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 250109. KimGoon. 단건 조회는 안 쓸 듯.
# # Prompt 데이터 조회
# @data_api.get("/prompt/get/{prompt_nm}")
# def get_prompt(prompt_nm: str):
#     """
#     지정된 이름의 Prompt 데이터를 조회합니다.
#     """
#     try:
#         result = DatabaseService.get_prompt(prompt_nm)
#         if not result:
#             raise HTTPException(status_code=404, detail="Prompt not found")
#         return {"data": result}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# Prompt 데이터 전체 조회
@data_api.get("/prompt/getAll")
def get_all_prompt():
    """
    전체 Prompt 데이터 리스트를 조회합니다.
    """
    try:
        result = DatabaseService.get_all_prompt()
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
        success = DatabaseService.add_prompt(prompt.node_nm, prompt.prompt_nm, prompt.prompt)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to insert prompt data")
        return {"message": "Prompt added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Prompt 데이터 삭제
@data_api.delete("/prompt/delete")
def delete_prompt(prompt: PromptInput):
    """
    Prompt 데이터를 삭제합니다.
    """
    try:
        result = DatabaseService.delete_prompt(prompt.node_nm, prompt.prompt_nm)
        return {"message": "Prompt data deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




# PostgreSQL에서 Few-shot 데이터 조회
@data_api.post("/fewshot/get")
def get_postgre_few_shot(data: PostgreToVectorData):
    """
    PostgreSQL에서 Few-shot 데이터를 조회합니다.
    """
    try:
        result = DatabaseService.get_postgre_few_shot(data)
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# PostgreSQL에서 Few-shot 데이터 전체 조회
@data_api.post("/fewshot/getAll")
def getAll_postgre_few_shot():
    """
    PostgreSQL에서 Few-shot 데이터를 전체 조회합니다.
    """
    try:
        result = DatabaseService.getAll_postgre_few_shot()
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Few-shot 데이터 추가
@data_api.post("/fewshot/add")
def add_few_shot(data: PostgreToVectorData):
    """
    새 벡터 데이터를 추가하고 임베딩 시스템에 업데이트합니다.
    """
    try:
        success = DatabaseService.add_few_shot(data)

        return {"message": "Few-shot data added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Few-shot 데이터 리스트 추가
@data_api.post("/fewshot/addList")
def add_list_few_shot(data: PostgreToVectorData):
    """
    새 벡터 데이터를 추가하고 임베딩 시스템에 업데이트합니다.
    """
    try:
        success = DatabaseService.add_list_few_shot(data)

        return {"message": "Few-shot data list added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Few-shot 데이터 업데이트
@data_api.put("/fewshot/update")
def update_few_shot(data: PostgreToVectorData):
    """
    벡터 데이터를 업데이트하고 임베딩 시스템을 수정합니다.
    """
    try:
        # success = DatabaseService.delete_few_shot(data)
        success = DatabaseService.multi_delete_few_shot(data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete vector data")

        success = DatabaseService.add_few_shot(data)

        return {"message": "Few-shot data updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Few-shot 데이터 삭제
@data_api.delete("/fewshot/delete")
def delete_few_shot(data: PostgreToVectorData):
    """
    벡터 데이터를 삭제하고 임베딩 시스템에서 제거합니다.
    """
    try:
        # success = DatabaseService.delete_few_shot(data)
        success = DatabaseService.multi_delete_few_shot(data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete vector data")
        return {"message": "Few-shot data deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))