from fastapi import APIRouter, HTTPException
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

from api.dto import RecommendRequest, RecommendCtgryRequest
from database.database_service import DatabaseService

recommend_api = APIRouter(tags=["recommend"])


# 홈 화면 추천질의 데이터 조회
@recommend_api.get("/getHome")
@cache(expire=60*60, namespace="home_recommend")
# @cache(expire=None, namespace="home_recommend")
def get_home_recommend():
    """
    홈 화면 내 추천질의 더보기 데이터를 조회합니다.
    """
    try:
        print("Cache created : home_recommend")

        result = DatabaseService.get_home_recommend()

        return {"body": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 추천질의 데이터 전체 조회
@recommend_api.get("/getAll")
def get_all_recommend():
    """
    추천질의 데이터를 전체 조회합니다.
    """
    try:
        result = DatabaseService.get_all_recommend()

        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 추천질의 데이터 단건 조회
@recommend_api.get("/get/{seq}")
def get_recommend(seq: int):
    """
    추천질의 데이터를 단건 조회합니다.
    """
    try:
        result = DatabaseService.get_recommend(seq)
        if result:
            result = result[0]

        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 추천질의 데이터 추가
@recommend_api.post("/add")
def add_recommend(data: RecommendRequest):
    """
    추천질의 데이터를 추가합니다.
    """
    try:
        seq = DatabaseService.insert_recommend(data)
        if not seq:
            raise HTTPException(status_code=500, detail="Failed to insert Recommend data")

        FastAPICache.clear("home_recommend")

        return {
            "status": 200,
            "success": True,
            "message": "Recommend data inserted successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 추천질의 데이터 수정
@recommend_api.put("/update")
def update_recommend(data: RecommendRequest):
    """
    추천질의 데이터를 수정합니다.
    """
    try:
        success = DatabaseService.update_recommend(data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update Recommend data")

        FastAPICache.clear("home_recommend")

        return {
            "status": 200,
            "success": True,
            "message": "Recommend data updated successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 추천질의 데이터 삭제
@recommend_api.delete("/delete/{seq}")
def delete_recommend(seq: int):
    """
    추천질의 데이터를 삭제합니다.
    """
    try:
        success = DatabaseService.delete_recommend(seq)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete Recommend data")

        FastAPICache.clear("home_recommend")

        return {
            "status": 200,
            "success": True,
            "message": "Recommend data deleted successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




# 추천질의 카테고리 데이터 전체 조회
@recommend_api.get("/ctgry/getAll")
def get_all_recommend_ctgry():
    """
    추천질의 카테고리 데이터를 전체 조회합니다.
    """
    try:
        result = DatabaseService.get_all_recommend_ctgry()

        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 추천질의 카테고리 데이터 단건 조회
@recommend_api.get("/ctgry/get/{ctgryCd}")
def get_recommend_ctgry(ctgryCd: str):
    """
    추천질의 카테고리 데이터를 단건 조회합니다.
    """
    try:
        result = DatabaseService.get_recommend_ctgry(ctgryCd)
        if result:
            result = result[0]

        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 추천질의 카테고리 데이터 추가
@recommend_api.post("/ctgry/add")
def add_recommend_ctgry(data: RecommendCtgryRequest):
    """
    추천질의 카테고리 데이터를 추가합니다.
    """
    try:
        seq = DatabaseService.insert_recommend_ctgry(data)
        if not seq:
            raise HTTPException(status_code=500, detail="Failed to insert Recommend Ctgry data")

        return {
            "status": 200,
            "success": True,
            "message": "Recommend Ctgry data inserted successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 추천질의 카테고리 데이터 수정
@recommend_api.put("/ctgry/update")
def update_recommend_ctgry(data: RecommendCtgryRequest):
    """
    추천질의 카테고리 데이터를 수정합니다.
    """
    try:
        success = DatabaseService.update_recommend_ctgry(data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update Recommend Ctgry data")

        FastAPICache.clear("home_recommend")

        return {
            "status": 200,
            "success": True,
            "message": "Recommend Ctgry data updated successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 추천질의 카테고리 데이터 삭제
@recommend_api.delete("/ctgry/delete/{ctgryCd}")
def delete_recommend_ctgry(ctgryCd: str):
    """
    추천질의 카테고리 데이터를 삭제합니다.
    """
    try:
        success = DatabaseService.delete_recommend_ctgry(ctgryCd)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete Recommend Ctgry data")

        FastAPICache.clear("home_recommend")

        return {
            "status": 200,
            "success": True,
            "message": "Recommend Ctgry data deleted successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))