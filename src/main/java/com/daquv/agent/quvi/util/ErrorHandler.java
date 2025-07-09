package com.daquv.agent.quvi.util;

import lombok.extern.slf4j.Slf4j;

import java.util.HashMap;
import java.util.Map;

/**
 * 에러 처리 유틸리티 클래스
 * old_back_agent의 error_handler.py를 Java로 마이그레이션
 */
@Slf4j
public class ErrorHandler {

    /**
     * 에러 코드 열거형
     */
    public enum ErrorCode {
        // Data related errors
        NO_DATA("DATA_001"),
        DATA_ACCESS_DENIED("DATA_002"),
        INVALID_DATE("DATA_003"),
        
        // Query related errors
        INVALID_QUERY("QUERY_001"),
        TABLE_NOT_FOUND("QUERY_002"),
        QUERY_SAFE_ERROR("QUERY_003"),
        
        // Access related errors
        COMPANY_ACCESS_DENIED("ACCESS_001"),
        INVALID_COMPANY("ACCESS_002"),
        
        // Input related errors
        INVALID_INPUT("INPUT_001"),
        FUTURE_DATE("INPUT_002"),
        
        // System errors
        DATABASE_ERROR("SYS_001"),
        LLM_ERROR("SYS_002"),
        NETWORK_ERROR("SYS_003"),
        UNKNOWN_ERROR("SYS_999");

        private final String code;

        ErrorCode(String code) {
            this.code = code;
        }

        public String getCode() {
            return code;
        }
    }

    // 프론트엔드에 표시할 사용자 친화적 메시지
    private static final Map<ErrorCode, String> USER_MESSAGES = new HashMap<>();
    
    static {
        USER_MESSAGES.put(ErrorCode.NO_DATA, "요청하신 데이터가 존재하지 않습니다.");
        USER_MESSAGES.put(ErrorCode.DATA_ACCESS_DENIED, "해당 데이터에 대한 접근 권한이 없습니다.");
        USER_MESSAGES.put(ErrorCode.INVALID_DATE, "날짜 형식이 올바르지 않습니다.");
        
        USER_MESSAGES.put(ErrorCode.INVALID_QUERY, "SQL 쿼리 실행 시 오류가 발생했습니다. 쿼리를 확인하시거나 담당자에게 문의해주세요.");
        USER_MESSAGES.put(ErrorCode.TABLE_NOT_FOUND, "요청하신 데이터 테이블을 찾을 수 없습니다.");
        
        USER_MESSAGES.put(ErrorCode.COMPANY_ACCESS_DENIED, "해당 기업의 데이터에 대한 접근 권한이 없습니다.");
        USER_MESSAGES.put(ErrorCode.INVALID_COMPANY, "유효하지 않은 회사명입니다.");
        
        USER_MESSAGES.put(ErrorCode.INVALID_INPUT, "입력하신 내용을 이해할 수 없습니다. 다시 한 번 확인해주세요.");
        USER_MESSAGES.put(ErrorCode.FUTURE_DATE, "미래 날짜의 데이터는 조회할 수 없습니다.");
        
        USER_MESSAGES.put(ErrorCode.DATABASE_ERROR, "데이터베이스 연결에 문제가 발생했습니다. 데이터베이스 서버 연결에 문제가 없는지 확인해주세요.");
        USER_MESSAGES.put(ErrorCode.LLM_ERROR, "AI 모델 처리 중 문제가 발생했습니다. 모델 서버가 제대로 실행 중인지 확인해주세요.");
        USER_MESSAGES.put(ErrorCode.NETWORK_ERROR, "네트워크 연결에 문제가 발생했습니다. 잠시 후 다시 시도해주세요.");
        USER_MESSAGES.put(ErrorCode.UNKNOWN_ERROR, "파악되지 않는 에러입니다. 담당자에게 문의해주세요.");
    }

    /**
     * 에러 타입을 분류하고 적절한 HTTP 상태 코드를 반환
     */
    public static ErrorInfo classifyError(Exception error) {
        String errorMessage = error.getMessage().toLowerCase();
        
        // 데이터 관련 에러
        if (errorMessage.contains("no data") || errorMessage.contains("not found")) {
            return new ErrorInfo(ErrorCode.NO_DATA, 404, null);
        } else if (errorMessage.contains("permission") || errorMessage.contains("access denied")) {
            return new ErrorInfo(ErrorCode.COMPANY_ACCESS_DENIED, 403, null);
        } else if (errorMessage.contains("date") && errorMessage.contains("future")) {
            return new ErrorInfo(ErrorCode.FUTURE_DATE, 400, null);
        } else if (errorMessage.contains("date") && (errorMessage.contains("invalid") || errorMessage.contains("format"))) {
            return new ErrorInfo(ErrorCode.INVALID_DATE, 400, null);
        }
        
        // 쿼리 관련 에러
        else if (errorMessage.contains("sql") || errorMessage.contains("invalid query")) {
            return new ErrorInfo(ErrorCode.INVALID_QUERY, 500, null);
        } else if (errorMessage.contains("table not found") || errorMessage.contains("relation does not exist")) {
            return new ErrorInfo(ErrorCode.TABLE_NOT_FOUND, 404, null);
        }
        
        // 시스템 에러
        else if (errorMessage.contains("database") || errorMessage.contains("connection")) {
            return new ErrorInfo(ErrorCode.DATABASE_ERROR, 503, null);
        } else if (errorMessage.contains("model") || errorMessage.contains("llm")) {
            return new ErrorInfo(ErrorCode.LLM_ERROR, 503, null);
        } else if (errorMessage.contains("network") || errorMessage.contains("timeout")) {
            return new ErrorInfo(ErrorCode.NETWORK_ERROR, 503, null);
        }
        
        // Safeguard 관련 에러
        else if (errorMessage.contains("query_result")) {
            return new ErrorInfo(ErrorCode.QUERY_SAFE_ERROR, 500, null);
        }
        
        return new ErrorInfo(ErrorCode.UNKNOWN_ERROR, 500, null);
    }

    /**
     * 에러를 API 응답 형식으로 변환
     */
    public static Map<String, Object> formatErrorResponse(Exception error) {
        log.error("Error occurred: {}", error.getMessage(), error);
        
        // Check for safeguard limit exceeded error
        if (error.getMessage() != null && error.getMessage().toLowerCase().contains("query_result")) {
            Map<String, Object> response = new HashMap<>();
            response.put("status", 500);
            response.put("success", false);
            response.put("retCd", 500);
            response.put("message", "죄송합니다. 아직 저는 이 질문에 답하기에 적합한 쿼리를 만들 수 없습니다. 그러나 저는 꾸준히 학습 중입니다. 곧 이 질문에 답할 수 있는 AICFO가 되어 도움을 드리겠습니다.");
            
            Map<String, Object> body = new HashMap<>();
            body.put("error_code", "QUERY_SAFE_LIMIT");
            body.put("detail", error.getMessage());
            response.put("body", body);
            
            return response;
        }
        
        ErrorInfo errorInfo = classifyError(error);
        String userMessage = USER_MESSAGES.get(errorInfo.getErrorCode());
        
        // 사용자 메시지와 상세 에러를 줄바꿈으로 구분
        String formattedMessage = userMessage + "\n\n" + error.getMessage();
        
        Map<String, Object> response = new HashMap<>();
        response.put("status", errorInfo.getStatusCode());
        response.put("success", false);
        response.put("retCd", errorInfo.getStatusCode());
        response.put("message", formattedMessage);
        
        Map<String, Object> body = new HashMap<>();
        body.put("error_code", errorInfo.getErrorCode().getCode());
        body.put("detail", error.getMessage());
        response.put("body", body);
        
        return response;
    }

    /**
     * 워크플로우 에러를 사용자 친화적 메시지로 변환
     */
    public static String getWorkflowErrorMessage(String errorType, String detail) {
        switch (errorType) {
            case "NO_DATA":
                return "요청하신 데이터가 존재하지 않습니다.";
            case "SQL_ERROR":
                return "SQL 쿼리 실행 중 오류가 발생했습니다. 다시 시도해주세요.";
            case "LLM_ERROR":
                return "AI 모델 처리 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.";
            case "TABLE_SELECTION_ERROR":
                return "적절한 데이터 테이블을 찾을 수 없습니다.";
            case "SAFEGUARD_ERROR":
                return "안전하지 않은 쿼리로 인해 실행이 중단되었습니다.";
            case "INVALID_INPUT":
                return "입력하신 내용을 이해할 수 없습니다. 다시 한 번 확인해주세요.";
            case "UNKNOWN_ERROR":
                return "처리 중 오류가 발생했습니다. 다시 시도해주세요.";
            default:
                return "처리 중 오류가 발생했습니다. 다시 시도해주세요.";
        }
    }

    /**
     * 에러 정보를 담는 내부 클래스
     */
    public static class ErrorInfo {
        private final ErrorCode errorCode;
        private final int statusCode;
        private final String sqlQuery;

        public ErrorInfo(ErrorCode errorCode, int statusCode, String sqlQuery) {
            this.errorCode = errorCode;
            this.statusCode = statusCode;
            this.sqlQuery = sqlQuery;
        }

        public ErrorCode getErrorCode() {
            return errorCode;
        }

        public int getStatusCode() {
            return statusCode;
        }

        public String getSqlQuery() {
            return sqlQuery;
        }
    }
} 