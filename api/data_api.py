from fastapi import APIRouter, HTTPException

from api.dto import VectorDataQuery, PromptInput, FewshotInput
from database.database_service import DatabaseService

data_api = APIRouter(tags=["data"])


# Prompt 데이터 전체 조회
@data_api.get("/prompt/getAll")
def get_all_prompt():
    """
    전체 Prompt 데이터를 전체 조회합니다.
    """
    try:
        result = DatabaseService.get_all_prompt()

        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Prompt 데이터 단건 조회
@data_api.get("/prompt/get/{nodeNm}/{promptNm}")
def get_prompt(nodeNm: str, promptNm: str):
    """
    전체 Prompt 데이터를 단건 조회합니다.
    """
    try:
        database_service = DatabaseService()
        result = database_service.get_prompt(nodeNm, promptNm)

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
# @data_api.delete("/prompt/delete/{nodeNm}/{promptNm}")
# def delete_prompt(nodeNm: str, promptNm: str):
    """
    Prompt 데이터를 삭제합니다.
    """
    try:
        success = DatabaseService.delete_prompt(prompt.node_nm, prompt.prompt_nm)
        # success = DatabaseService.delete_prompt(nodeNm, promptNm)
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


# Few-shot 데이터 전체 조회
@data_api.post("/fewshot/getAll")
# @data_api.get("/fewshot/getAll")
def getAll_fewshot():
    """
    Few-shot 데이터를 전체 조회합니다.
    """
    try:
        result = DatabaseService.get_all_fewshot_vector()

        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Few-shot 데이터 단건 조회
@data_api.get("/fewshot/get/{title}")
def get_fewshot(title: str):
# @data_api.get("/fewshot/get/{collectionName}")
# def get_fewshot(collectionName: str):
    """
    Few-shot 데이터를 단건 조회합니다.
    """
    try:
        result = DatabaseService.get_fewshot_vector(title)
        # result = DatabaseService.get_fewshot_vector(collectionName)

        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Few-shot 전체 데이터 조회
@data_api.get("/fewshot/getAllRDB")
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
        # success = DatabaseService.add_fewshot_list(data.title, data.shots)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add fewshot data")

        return {
            "status": 200,
            "success": True,
            "message": "Few-shot data added successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Few-shot 데이터 전체 삭제
@data_api.delete("/fewshot/delete")
def delete_fewshot(data: FewshotInput):
# @data_api.delete("/fewshot/delete/{collectionName}")
# def delete_fewshot(collectionName: str):
    """
    벡터 데이터를 삭제하고 임베딩 시스템에서 제거합니다.
    """
    try:
        success = DatabaseService.collection_delete_fewshot(data.title)
        # success = DatabaseService.collection_delete_fewshot(collectionName)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete fewshot data")

        return {
            "status": 200,
            "success": True,
            "message": "Few-shot data deleted successfully",
        }
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

        return {
            "status": 200,
            "success": True,
            "message": "Few-shot data restored successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))