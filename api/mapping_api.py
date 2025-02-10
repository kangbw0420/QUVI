from fastapi import APIRouter, HTTPException

from api.dto import MappingRequest
from database.database_service import DatabaseService

mapping_api = APIRouter(tags=["mapping"])


# 컬럼명 관리 데이터 전체 조회
@mapping_api.get("/getAll")
@mapping_api.post("/getAll")
def get_all_mapping():
    """
    컬럼명 관리 데이터를 전체 조회합니다.
    """
    try:
        result = DatabaseService.get_all_mapping()
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 컬럼명 관리 데이터 추가
@mapping_api.post("/add")
def add_mapping(data: MappingRequest):
    """
    컬럼명 관리 데이터를 추가합니다.
    """
    try:
        success = DatabaseService.insert_mapping(data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to insert mapping data")
        return {
            "status": 200,
            "success": True,
            "message": "Mapping data added successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 컬럼명 관리 데이터 수정
@mapping_api.put("/update")
def update_mapping(data: MappingRequest):
    """
    컬럼명 관리 데이터를 수정합니다.
    """
    try:
        success = DatabaseService.update_mapping(data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update mapping data")
        return {
            "status": 200,
            "success": True,
            "message": "Mapping data updated successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 컬럼명 관리 데이터 삭제
@mapping_api.delete("/delete")
def delete_mapping(data: MappingRequest):
    """
    컬럼명 관리 데이터를 삭제합니다.
    """
    try:
        success = DatabaseService.delete_mapping(data.idx)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete mapping data")
        return {
            "status": 200,
            "success": True,
            "message": "Mapping data deleted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))