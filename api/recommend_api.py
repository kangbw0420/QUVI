from fastapi import APIRouter, HTTPException

from database.database_service import DatabaseService

recommend_api = APIRouter(tags=["recommend"])


# 홈 화면 추천질의 데이터 조회
@recommend_api.get("/getHome")
@recommend_api.post("/getHome")
def get_home_recommend():
    """
    홈 화면 내 추천질의 더보기 데이터를 조회합니다.
    """
    try:
        result = DatabaseService.get_home_recommend()

        return {"body": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))