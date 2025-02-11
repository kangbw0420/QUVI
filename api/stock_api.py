from fastapi import APIRouter, HTTPException

from api.dto import StockRequest
from database.database_service import DatabaseService

stock_api = APIRouter(tags=["stock"])


# 주식명 유의어 관리 데이터 전체 조회
@stock_api.get("/getAll")
def get_all_stock():
    """
    주식명 유의어 관리 데이터를 전체 조회합니다.
    """
    try:
        result = DatabaseService.get_all_stock()

        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 주식명 유의어 관리 데이터 추가
@stock_api.post("/add")
def add_stock(data: StockRequest):
    """
    주식명 유의어 관리 데이터를 추가합니다.
    """
    try:
        for stockNickNm in data.stockNickNmList:
            data["stockNickNm"] = stockNickNm
            success = DatabaseService.insert_stock(data)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to insert stock data")

        return {
            "status": 200,
            "success": True,
            "message": "Stock data added successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 주식명 유의어 관리 데이터 수정
@stock_api.put("/update")
def update_stock(data: StockRequest):
    """
    주식명 유의어 관리 데이터를 수정합니다.
    """
    try:
        success = DatabaseService.delete_stock(data.stockCd)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete stock data")

        success = DatabaseService.insert_stock_list(data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to insert stock data")

        return {
            "status": 200,
            "success": True,
            "message": "Stock data updated successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 주식명 유의어 관리 데이터 삭제
@stock_api.delete("/delete")
def delete_stock(data: StockRequest):
    """
    주식명 유의어 관리 데이터를 삭제합니다.
    """
    try:
        success = DatabaseService.delete_stock(data.stockCd)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete stock data")

        return {
            "status": 200,
            "success": True,
            "message": "Stock data deleted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))