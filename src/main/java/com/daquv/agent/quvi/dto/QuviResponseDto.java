package com.daquv.agent.quvi.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Quvi API 응답 DTO
 */

@Data
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class QuviResponseDto {
    private int status;           // HTTP 상태 코드
    private boolean success;      // 성공 여부
    private int retCd;           // 응답 코드
    private String message;      // 응답 메시지
    private Object body;         // 응답 본문 (AnswerBody 또는 Map)
} 