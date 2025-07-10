package com.daquv.agent.quvi.requests;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.ArrayList;
import java.util.Set;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.type.TypeReference;

@Component
public class ColumnRequest {
    
    private static final Logger log = LoggerFactory.getLogger(ColumnRequest.class);

    private final RestTemplate restTemplate = new RestTemplate();
    private static final String COLUMN_API_BASE_URL = "http://localhost:8106/column";

    /**
     * SQL 쿼리에서 특정 컬럼의 조건을 찾아 반환
     * Python: /column/column_conditions 엔드포인트
     */
    public List<String> findColumnConditions(String query, String columnName) {
        try {
            log.info("[column] column_conditions API 호출 - 쿼리: {}, 컬럼명: {}", query, columnName);

            // 요청 데이터 구성
            Map<String, Object> requestData = new HashMap<>();
            requestData.put("query", query);
            requestData.put("column_name", columnName);

            // HTTP 헤더 설정
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            // HTTP 요청 생성
            HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestData, headers);

            // API 호출
            ResponseEntity<String> response = restTemplate.postForEntity(
                COLUMN_API_BASE_URL + "/column_conditions", request, String.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                String result = response.getBody();
                log.info("[column] column_conditions API 호출 성공 - 결과: {}", result);
                
                // JSON 응답에서 column_values 필드 추출
                if (result != null && !result.trim().isEmpty()) {
                    try {
                        ObjectMapper objectMapper = new ObjectMapper();
                        JsonNode jsonNode = objectMapper.readTree(result);
                        List<String> conditions = objectMapper.convertValue(
                            jsonNode.get("column_values"), 
                            new TypeReference<List<String>>() {}
                        );
                        
                        log.info("[column] 추출된 조건들: {}", conditions);
                        return conditions;
                    } catch (Exception e) {
                        log.error("[column] JSON 파싱 중 오류: {}", e.getMessage(), e);
                        return new ArrayList<>();
                    }
                } else {
                    return new ArrayList<>();
                }
            } else {
                log.error("[column] column_conditions API 호출 실패 - 상태 코드: {}", response.getStatusCode());
                return new ArrayList<>();
            }

        } catch (Exception e) {
            log.error("[column] column_conditions API 호출 중 예외 발생: {}", e.getMessage(), e);
            return new ArrayList<>();
        }
    }

    /**
     * note1 조건을 찾아 반환 (ever_note용)
     * Python: /column/column_conditions 엔드포인트의 상세 버전
     */
    public List<Map<String, Object>> findNoteConditions(String query) {
        try {
            log.info("[column] find_note_conditions API 호출 - 쿼리: {}", query);

            // 요청 데이터 구성
            Map<String, Object> requestData = new HashMap<>();
            requestData.put("query", query);
            requestData.put("column_name", "note1");

            // HTTP 헤더 설정
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            // HTTP 요청 생성
            HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestData, headers);

            // API 호출
            ResponseEntity<String> response = restTemplate.postForEntity(
                COLUMN_API_BASE_URL + "/column_conditions", request, String.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                String result = response.getBody();
                log.info("[column] find_note_conditions API 호출 성공 - 결과: {}", result);
                
                // JSON 응답에서 column_conditions 필드 추출
                if (result != null && !result.trim().isEmpty()) {
                    try {
                        ObjectMapper objectMapper = new ObjectMapper();
                        JsonNode jsonNode = objectMapper.readTree(result);
                        List<Map<String, Object>> conditions = objectMapper.convertValue(
                            jsonNode.get("column_conditions"), 
                            new TypeReference<List<Map<String, Object>>>() {}
                        );
                        
                        log.info("[column] 추출된 note 조건들: {}", conditions);
                        return conditions;
                    } catch (Exception e) {
                        log.error("[column] JSON 파싱 중 오류: {}", e.getMessage(), e);
                        return new ArrayList<>();
                    }
                } else {
                    return new ArrayList<>();
                }
            } else {
                log.error("[column] find_note_conditions API 호출 실패 - 상태 코드: {}", response.getStatusCode());
                return new ArrayList<>();
            }

        } catch (Exception e) {
            log.error("[column] find_note_conditions API 호출 중 예외 발생: {}", e.getMessage(), e);
            return new ArrayList<>();
        }
    }

    /**
     * 유사한 노트로 쿼리 변환
     * Python: /column/ever_note 엔드포인트
     */
    public String transformQueryWithSimilarNotes(String query, List<Map<String, Object>> noteConditions, Set<String> similarNotes) {
        try {
            log.info("[column] ever_note API 호출 - 쿼리: {}, 조건수: {}, 유사노트수: {}", 
                     query, noteConditions.size(), similarNotes.size());

            // 유사 노트 매핑 생성 (Python API 가이드에 맞춤)
            Map<String, List<String>> similarNotesMapping = new HashMap<>();
            for (Map<String, Object> condition : noteConditions) {
                String originalNote = (String) condition.get("value");
                if (originalNote != null) {
                    similarNotesMapping.put(originalNote, new ArrayList<>(similarNotes));
                }
            }

            // 요청 데이터 구성
            Map<String, Object> requestData = new HashMap<>();
            requestData.put("query", query);
            requestData.put("note_conditions", noteConditions);
            requestData.put("similar_notes_mapping", similarNotesMapping);

            // HTTP 헤더 설정
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            // HTTP 요청 생성
            HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestData, headers);

            // API 호출
            ResponseEntity<String> response = restTemplate.postForEntity(
                COLUMN_API_BASE_URL + "/ever_note", request, String.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                String result = response.getBody();
                log.info("[column] ever_note API 호출 성공 - 결과: {}", result);
                
                // JSON 응답에서 query 필드 추출
                if (result != null && !result.trim().isEmpty()) {
                    try {
                        ObjectMapper objectMapper = new ObjectMapper();
                        JsonNode jsonNode = objectMapper.readTree(result);
                        String transformedQuery = jsonNode.get("query").asText();
                        
                        log.info("[column] 변환된 SQL 쿼리: {}", transformedQuery);
                        return transformedQuery;
                    } catch (Exception e) {
                        log.error("[column] JSON 파싱 중 오류: {}", e.getMessage(), e);
                        return query; // 오류 발생 시 원본 쿼리 반환
                    }
                } else {
                    return query;
                }
            } else {
                log.error("[column] ever_note API 호출 실패 - 상태 코드: {}", response.getStatusCode());
                return query;
            }

        } catch (Exception e) {
            log.error("[column] ever_note API 호출 중 예외 발생: {}", e.getMessage(), e);
            return query;
        }
    }
}