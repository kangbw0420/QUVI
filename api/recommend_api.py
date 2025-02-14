from fastapi import APIRouter, HTTPException
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

from api.dto import RecommendRequest
from database.database_service import DatabaseService

recommend_api = APIRouter(tags=["recommend"])


# 홈 화면 추천질의 데이터 조회
@recommend_api.get("/getHome")
@recommend_api.post("/getHome")
@cache(namespace="home_recommend", expire=60)
def get_home_recommend():
    """
    홈 화면 내 추천질의 더보기 데이터를 조회합니다.
    """
    try:
        result = DatabaseService.get_home_recommend()

        return {"body": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
