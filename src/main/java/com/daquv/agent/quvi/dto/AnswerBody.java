package com.daquv.agent.quvi.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

/**
 * Quvi API 응답 본문 DTO
 */

@Data
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class AnswerBody {
    private String answer;                    // 답변
    private List<Map<String, Object>> rawData; // 원시 데이터
    private String sessionId;                 // 세션 ID
    private String chainId;                   // 체인 ID
    private List<String> recommend;           // 추천 질문 리스트
    private DateInfo dateInfo;                // 날짜 정보
    private String sqlQuery;                  // SQL 쿼리
    private String selectedTable;             // 선택된 테이블
    private boolean hasNext;                  // 다음 페이지 여부
    private Map<String, Object> profile;      // 프로파일링 정보
} 