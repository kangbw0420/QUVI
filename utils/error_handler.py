from enum import Enum
from typing import Optional, Dict, Any
from fastapi import HTTPException

class ErrorCode(Enum):
    # 데이터 관련 에러
    NO_DATA = "DATA_001"
    DATA_ACCESS_DENIED = "DATA_002"
    INVALID_DATE = "DATA_003"
    
    # 사용자 입력 관련 에러
    INVALID_INPUT = "INPUT_001"
    INVALID_COMPANY = "INPUT_002"
    
    # 시스템 에러
    DATABASE_ERROR = "SYS_001"
    LLM_ERROR = "SYS_002"
    UNKNOWN_ERROR = "SYS_999"

class ErrorMessage:
    # 에러 메시지 매핑
    ERROR_MESSAGES = {
        ErrorCode.NO_DATA: "요청하신 데이터가 존재하지 않습니다.",
        ErrorCode.DATA_ACCESS_DENIED: "해당 데이터에 대한 접근 권한이 없습니다.",
        ErrorCode.INVALID_DATE: "날짜 형식이 올바르지 않습니다.",
        
        ErrorCode.INVALID_INPUT: "입력하신 내용을 이해할 수 없습니다. 다시 한 번 확인해주세요.",
        ErrorCode.INVALID_COMPANY: "유효하지 않은 회사명입니다.",
        
        ErrorCode.DATABASE_ERROR: "데이터베이스 조회 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.",
        ErrorCode.LLM_ERROR: "AI 모델 처리 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.",
        ErrorCode.UNKNOWN_ERROR: "처리 중 예상치 못한 문제가 발생했습니다. 잠시 후 다시 시도해주세요."
    }

class ErrorHandler:
    @staticmethod
    def classify_error(error: Exception) -> ErrorCode:
        """에러 타입과 메시지를 기반으로 ErrorCode 분류"""
        error_message = str(error).lower()
        
        if isinstance(error, HTTPException):
            if error.status_code == 404:
                return ErrorCode.NO_DATA
            elif error.status_code == 403:
                return ErrorCode.DATA_ACCESS_DENIED
                
        # 데이터 관련 에러
        if "no data" in error_message or "not found" in error_message:
            return ErrorCode.NO_DATA
        elif "permission" in error_message or "access denied" in error_message:
            return ErrorCode.DATA_ACCESS_DENIED
        elif "date" in error_message and ("invalid" in error_message or "format" in error_message):
            return ErrorCode.INVALID_DATE
            
        # 사용자 입력 관련 에러
        elif "company" in error_message and "invalid" in error_message:
            return ErrorCode.INVALID_COMPANY
        elif "input" in error_message and "invalid" in error_message:
            return ErrorCode.INVALID_INPUT
            
        # 시스템 에러
        elif "database" in error_message:
            return ErrorCode.DATABASE_ERROR
        elif "model" in error_message or "llm" in error_message:
            return ErrorCode.LLM_ERROR
            
        return ErrorCode.UNKNOWN_ERROR

    @staticmethod
    def format_error_response(error: Exception) -> Dict[str, Any]:
        """에러를 사용자 친화적인 응답 형식으로 변환"""
        error_code = ErrorHandler.classify_error(error)
        user_message = ErrorMessage.ERROR_MESSAGES[error_code]
        
        return {
            "status": 500,
            "success": False,
            "retCd": 500,
            "message": user_message,
            "body": {
                "error_code": error_code.value,
                "original_error": str(error)
            }
        }