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

        return {
            "status": 200,
            "success": True,
            "message": "Mapping data inserted successfully",
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
            "message": "Mapping data updated successfully",
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
            "message": "Mapping data deleted successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))