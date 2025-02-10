from fastapi import APIRouter, HTTPException

from api.dto import PostgreToVectorData, VectorDataQuery, PromptInput, FewshotInput
from database.database_service import DatabaseService

data_api = APIRouter(tags=["data"])


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


# Prompt 데이터 조회
@data_api.get("/prompt/get/{node_nm}/{prompt_nm}")
def get_prompt(node_nm:str, prompt_nm: str):
    """
    지정된 이름의 Prompt 데이터를 조회합니다.
    """
    try:
        result = DatabaseService.get_prompt(node_nm, prompt_nm)
        if not result:
            raise HTTPException(status_code=500, detail="Prompt not found")
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
        return {
            "status": 200,
            "success": True,
            "message": "Prompt data added successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Prompt 데이터 삭제
@data_api.delete("/prompt/delete")
def delete_prompt(prompt: PromptInput):
    """
    Prompt 데이터를 삭제합니다.
    """
    try:
        success = DatabaseService.delete_prompt(prompt.node_nm, prompt.prompt_nm)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete prompt data")
        return {
            "status": 200,
            "success": True,
            "message": "Prompt data deleted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




# Few-shot 데이터 검색
@data_api.post("/fewshot/query")
def query_fewshot(data: VectorDataQuery):
    """
    Few-shot 데이터를 검색합니다.
    """
    try:
        result = DatabaseService.query_fewshot_vector(data)
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Few-shot 전체 데이터 조회
@data_api.post("/fewshot/getAll")
def getAll_fewshot():
    """
    Few-shot 전체 데이터를 조회합니다.
    """
    try:
        result = DatabaseService.get_all_fewshot_vector()
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Few-shot 데이터 조회
@data_api.get("/fewshot/get/{title}")
def get_fewshot(title: str):
    """
    Few-shot 데이터를 조회합니다.
    """
    try:
        result = DatabaseService.get_fewshot_vector(title)
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Few-shot 전체 데이터 조회
@data_api.post("/fewshot/getAllRDB")
def getAllRDB_fewshot():
    """
    RDB 에서 Few-shot 전체 데이터를 조회합니다.
    """
    try:
        result = DatabaseService.get_all_fewshot_rdb()
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Few-shot 데이터 추가
@data_api.post("/fewshot/add")
def add_fewshot(data: FewshotInput):
    """
    새 벡터 데이터를 추가하고 임베딩 시스템에 업데이트합니다.
    """
    try:
        success = DatabaseService.add_fewshot(data.title, data.shots)
        # success = DatabaseService.addList_fewshot(data.title, data.shots)
        return {"message": "Few-shot data added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Few-shot 데이터 전체 삭제
@data_api.delete("/fewshot/delete")
def delete_fewshot(data: FewshotInput):
    """
    벡터 데이터를 삭제하고 임베딩 시스템에서 제거합니다.
    """
    try:
        success = DatabaseService.collection_delete_fewshot(data.title)
        return {"message": "Few-shot data deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Few-shot 휘발데이터 복구
@data_api.post("/fewshot/restore")
def restore_fewshot():
    """
    벡터 DB 재기동 시 RDB 의 최신 데이터를 기반으로 벡터 데이터 복구
    """
    try:
        result = DatabaseService.get_all_fewshot_rdb()
        DatabaseService.restore_fewshot(result)
        return {"message": "Few-shot data restored successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))