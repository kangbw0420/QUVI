package com.daquv.agent.quvi.dto;

/**
 * 알림 타입 열거형
 */
public enum AlertType {
    ERROR("에러 발생"),
    SQL_ERROR("SQL 에러"),
    CONSECUTIVE_FAILURE("연속 실패"),
    SLOW_RESPONSE("응답 지연"),
    VECTOR_CONNECTION_FAILURE("벡터 스토어 연결 실패"),
    API_CONNECTION_FAILURE("API 연결 실패"),
    FILE_NOT_FOUND("파일 누락"),
    CUSTOM("사용자 정의");

    private final String description;

    AlertType(String description) {
        this.description = description;
    }

    public String getDescription() {
        return description;
    }
}