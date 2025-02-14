from enum import Enum
from typing import Dict, Any, Tuple
from fastapi import HTTPException

class ErrorCode(Enum):
    # Data related errors
    NO_DATA = "DATA_001"
    DATA_ACCESS_DENIED = "DATA_002"
    INVALID_DATE = "DATA_003"
    
    # Query related errors
    INVALID_QUERY = "QUERY_001"
    TABLE_NOT_FOUND = "QUERY_002"
    
    # Access related errors
    COMPANY_ACCESS_DENIED = "ACCESS_001"
    INVALID_COMPANY = "ACCESS_002"
    
    # Input related errors
    INVALID_INPUT = "INPUT_001"
    FUTURE_DATE = "INPUT_002"
    
    # System errors
    DATABASE_ERROR = "SYS_001"
    LLM_ERROR = "SYS_002"
    NETWORK_ERROR = "SYS_003"
    UNKNOWN_ERROR = "SYS_999"

class ErrorHandler:
    # 프론트엔드에 표시할 사용자 친화적 메시지
    USER_MESSAGES = {
        ErrorCode.NO_DATA: " 요청하신 데이터가 존재하지 않습니다.",
        ErrorCode.DATA_ACCESS_DENIED: " 해당 데이터에 대한 접근 권한이 없습니다.",
        ErrorCode.INVALID_DATE: " 날짜 형식이 올바르지 않습니다.",
        
        ErrorCode.INVALID_QUERY: " 검색 조건이 올바르지 않습니다.",
        ErrorCode.TABLE_NOT_FOUND: " 요청하신 데이터 테이블을 찾을 수 없습니다.",
        
        ErrorCode.COMPANY_ACCESS_DENIED: " 해당 기업의 데이터에 대한 접근 권한이 없습니다.",
        ErrorCode.INVALID_COMPANY: " 유효하지 않은 회사명입니다.",
        
        ErrorCode.INVALID_INPUT: " 입력하신 내용을 이해할 수 없습니다. 다시 한 번 확인해주세요.",
        ErrorCode.FUTURE_DATE: " 미래 날짜의 데이터는 조회할 수 없습니다.",
        
        ErrorCode.DATABASE_ERROR: " 데이터베이스 연결에 문제가 발생했습니다. 데이터베이스 서버 연결에 문제가 없는지 확인해주세요.",
        ErrorCode.LLM_ERROR: " AI 모델 처리 중 문제가 발생했습니다. 모델 서버가 제대로 실행 중인지 확인해주세요.",
        ErrorCode.NETWORK_ERROR: " 네트워크 연결에 문제가 발생했습니다. 잠시 후 다시 시도해주세요.",
        ErrorCode.UNKNOWN_ERROR: " 파악되지 않는 에러입니다. 담당자에게 문의해주세요."
    }

    @staticmethod
    def classify_error(error: Exception) -> Tuple[ErrorCode, int]:
        """에러 타입을 분류하고 적절한 HTTP 상태 코드를 반환"""
        error_message = str(error).lower()
        
        # HTTP 예외 처리
        if isinstance(error, HTTPException):
            if error.status_code == 404:
                return ErrorCode.NO_DATA, 404
            elif error.status_code == 403:
                return ErrorCode.DATA_ACCESS_DENIED, 403
        
        # 데이터 관련 에러
        if "no data" in error_message or "not found" in error_message:
            return ErrorCode.NO_DATA, 404
        elif "permission" in error_message or "access denied" in error_message:
            return ErrorCode.COMPANY_ACCESS_DENIED, 403
        elif "date" in error_message and "future" in error_message:
            return ErrorCode.FUTURE_DATE, 400
        elif "date" in error_message and ("invalid" in error_message or "format" in error_message):
            return ErrorCode.INVALID_DATE, 400
            
        # 쿼리 관련 에러
        elif "syntax error" in error_message or "invalid query" in error_message:
            return ErrorCode.INVALID_QUERY, 400
        elif "table not found" in error_message or "relation does not exist" in error_message:
            return ErrorCode.TABLE_NOT_FOUND, 404
            
        # 시스템 에러
        elif "database" in error_message or "connection" in error_message:
            return ErrorCode.DATABASE_ERROR, 503
        elif "model" in error_message or "llm" in error_message:
            return ErrorCode.LLM_ERROR, 503
        elif "network" in error_message or "timeout" in error_message:
            return ErrorCode.NETWORK_ERROR, 503
            
        return ErrorCode.UNKNOWN_ERROR, 500

    @staticmethod
    def format_error_response(error: Exception) -> Dict[str, Any]:
        """에러를 API 응답 형식으로 변환"""
        error_code, status_code = ErrorHandler.classify_error(error)
        user_message = ErrorHandler.USER_MESSAGES[error_code]
        
        # 사용자 메시지와 상세 에러를 줄바꿈으로 구분
        formatted_message = f"{user_message}\n\n{str(error)}"
        
        return {
            "status": status_code,
            "success": False,
            "retCd": status_code,
            "message": formatted_message,
            "body": {
                "error_code": error_code.value,
                "detail": str(error)
            }
        }