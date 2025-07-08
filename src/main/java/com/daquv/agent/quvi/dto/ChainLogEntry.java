package com.daquv.agent.quvi.dto;

import com.daquv.agent.quvi.dto.LogLevel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 체인 로그 엔트리 - 개별 로그 항목
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ChainLogEntry {

    private LocalDateTime timestamp;
    private String nodeId;
    private LogLevel level;
    private String message;
    private Exception exception;
    private Object data; // 추가 데이터

    /**
     * 예외 스택 트레이스 반환
     */
    public String getStackTrace() {
        if (exception == null) return null;

        java.io.StringWriter sw = new java.io.StringWriter();
        java.io.PrintWriter pw = new java.io.PrintWriter(sw);
        exception.printStackTrace(pw);
        return sw.toString();
    }

    /**
     * 로그 메시지 포맷팅
     */
    public String getFormattedMessage() {
        StringBuilder sb = new StringBuilder();
        sb.append(String.format("[%s] [%s] [%s] %s",
                timestamp.toString(), level, nodeId, message));

        if (exception != null) {
            sb.append(" - Exception: ").append(exception.getMessage());
        }

        return sb.toString();
    }
}