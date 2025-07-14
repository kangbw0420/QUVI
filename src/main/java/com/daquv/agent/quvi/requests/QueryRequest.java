package com.daquv.agent.quvi.requests;

import com.daquv.agent.workflow.dto.UserInfo;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.*;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

@Component
public class QueryRequest {
    
    private static final Logger log = LoggerFactory.getLogger(QueryRequest.class);

    private final RestTemplate restTemplate = new RestTemplate();
    private final JdbcTemplate mainJdbcTemplate;
    @Value("${api.quvi-query}")
    private String QUERY_API_BASE_URL;

    @Value("${view-table.view-func}")
    private String VIEW_FUNCTION;
    public QueryRequest(@Qualifier("mainJdbcTemplate") JdbcTemplate mainJdbcTemplate) {
        this.mainJdbcTemplate = mainJdbcTemplate;
    }

    /**
     * SQL 쿼리가 반환할 총 행 수를 계산합니다.
     *
     * @param query SQL 쿼리
     * @param limitValue 제한 값
     * @return 총 행 수 (문자열로 반환)
     */
    public String countRows(String query, Integer limitValue) {
        try {
            log.info("[query] count_rows API 호출 시작");
            log.info("[query] 원본 쿼리: {}", query);
            log.info("[query] 제한 값: {}", limitValue);

            // 요청 데이터 구성
            Map<String, Object> requestData = new HashMap<>();
            requestData.put("query", query);
            requestData.put("limit_value", limitValue);

            log.info("[query] 요청 데이터: {}", requestData);

            // HTTP 헤더 설정
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            // HTTP 요청 생성
            HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestData, headers);

            // API 호출
            String apiUrl = QUERY_API_BASE_URL + "/pagination/count_rows";
            log.info("[query] API URL: {}", apiUrl);
            
            ResponseEntity<String> response = restTemplate.postForEntity(apiUrl, request, String.class);

            log.info("[query] API 응답 상태 코드: {}", response.getStatusCode());
            log.info("[query] API 응답 본문: {}", response.getBody());

            if (response.getStatusCode().is2xxSuccessful()) {
                String result = response.getBody();
                log.info("[query] count_rows API 호출 성공 - 결과: {}", result);
                
                // 결과 파싱 시도
                if (result != null && !result.trim().isEmpty()) {
                    try {
                        // JSON 응답에서 result 필드 추출
                        ObjectMapper objectMapper = new ObjectMapper();
                        JsonNode jsonNode = objectMapper.readTree(result);
                        String sqlQuery = jsonNode.get("result").asText();
                        
                        log.info("[query] 추출된 SQL 쿼리: {}", sqlQuery);
                        
                        // 실제 DB 쿼리 실행
                        Integer count = mainJdbcTemplate.queryForObject(sqlQuery, Integer.class);
                        log.info("[query] COUNT 쿼리 실행 결과: {}", count);
                        
                        if (count != null) {
                            log.info("[query] 최종 행 수: {}", count);
                            return count.toString();
                        } else {
                            log.warn("[query] COUNT 쿼리 결과가 null입니다");
                            return "0";
                        }
                    } catch (Exception e) {
                        log.error("[query] COUNT 쿼리 실행 중 오류: {}", e.getMessage(), e);
                        return "0";
                    }
                } else {
                    log.warn("[query] 빈 결과 반환됨");
                    return "0";
                }
            } else {
                log.error("[query] count_rows API 호출 실패 - 상태 코드: {}", response.getStatusCode());
                return "행 수 계산 중 오류가 발생했습니다.";
            }

        } catch (Exception e) {
            log.error("[query] count_rows API 호출 중 예외 발생: {}", e.getMessage(), e);
            return "행 수 계산 중 오류가 발생했습니다: " + e.getMessage();
        }
    }

    /**
     * view_table 함수
     */
    public String viewTable(String query, List<String> parameters, String dialect) {
        try {
            log.info("[query] view_table API 호출 - 쿼리: {}, 매개변수들: {}",
                     query, parameters);

            // 요청 데이터 구성
            Map<String, Object> requestData = new HashMap<>();
            requestData.put("query", query);
            requestData.put("parameters", parameters);


            requestData.put("dialect", dialect);
            requestData.put("view_func", VIEW_FUNCTION);
            // HTTP 헤더 설정
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            // HTTP 요청 생성
            HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestData, headers);

            // API 호출
            ResponseEntity<String> response = restTemplate.postForEntity(
                QUERY_API_BASE_URL + "/view_table", request, String.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                String result = response.getBody();
                log.info("[query] view_table API 호출 성공 - 결과: {}", result);
                
                // JSON 응답에서 result 필드 추출
                if (result != null && !result.trim().isEmpty()) {
                    try {
                        ObjectMapper objectMapper = new ObjectMapper();
                        JsonNode jsonNode = objectMapper.readTree(result);
                        String sqlQuery = jsonNode.get("result").asText();
                        
                        log.info("[query] 추출된 SQL 쿼리: {}", sqlQuery);
                        return sqlQuery;
                    } catch (Exception e) {
                        log.error("[query] JSON 파싱 중 오류: {}", e.getMessage(), e);
                        return query; // 오류 발생 시 원본 쿼리 반환
                    }
                } else {
                    return query;
                }
            } else {
                log.error("[query] view_table API 호출 실패 - 상태 코드: {}", response.getStatusCode());
                return query;
            }

        } catch (Exception e) {
            log.error("[query] view_table API 호출 중 예외 발생: {}", e.getMessage(), e);
            return query;
        }
    }

    /**
     * SQL 쿼리에 LIMIT과 OFFSET을 추가합니다.
     *
     * @param query SQL 쿼리
     * @param limitValue 제한 값
     * @param offsetValue 오프셋 값
     * @return LIMIT과 OFFSET이 추가된 쿼리 문자열
     */
    public String addLimits(String query, Integer limitValue, Integer offsetValue) {
        try {
            log.info("[query] add_limits API 호출 시작");
            log.info("[query] 원본 쿼리: {}", query);
            log.info("[query] 제한 값: {}, 오프셋 값: {}", limitValue, offsetValue);

            // 요청 데이터 구성
            Map<String, Object> requestData = new HashMap<>();
            requestData.put("query", query);
            requestData.put("limit_value", limitValue);
            requestData.put("offset_value", offsetValue);

            log.info("[query] 요청 데이터: {}", requestData);

            // HTTP 헤더 설정
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            // HTTP 요청 생성
            HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestData, headers);

            // API 호출
            String apiUrl = QUERY_API_BASE_URL + "/pagination/add_limits";
            log.info("[query] API URL: {}", apiUrl);
            
            ResponseEntity<String> response = restTemplate.postForEntity(apiUrl, request, String.class);

            log.info("[query] API 응답 상태 코드: {}", response.getStatusCode());
            log.info("[query] API 응답 본문: {}", response.getBody());

            if (response.getStatusCode().is2xxSuccessful()) {
                String result = response.getBody();
                log.info("[query] add_limits API 호출 성공 - 결과: {}", result);
                
                // JSON 응답에서 result 필드 추출
                if (result != null && !result.trim().isEmpty()) {
                    try {
                        ObjectMapper objectMapper = new ObjectMapper();
                        JsonNode jsonNode = objectMapper.readTree(result);
                        String sqlQuery = jsonNode.get("result").asText();
                        
                        log.info("[query] 추출된 SQL 쿼리: {}", sqlQuery);
                        return sqlQuery;
                    } catch (Exception e) {
                        log.error("[query] JSON 파싱 중 오류: {}", e.getMessage(), e);
                        return query; // 오류 발생 시 원본 쿼리 반환
                    }
                } else {
                    return query;
                }
            } else {
                log.error("[query] add_limits API 호출 실패 - 상태 코드: {}", response.getStatusCode());
                return "LIMIT/OFFSET 추가 중 오류가 발생했습니다.";
            }

        } catch (Exception e) {
            log.error("[query] add_limits API 호출 중 예외 발생: {}", e.getMessage(), e);
            return "LIMIT/OFFSET 추가 중 오류가 발생했습니다: " + e.getMessage();
        }
    }

    /**
     * 기존 쿼리의 OFFSET 값을 찾아서 limit_value를 더한 새로운 OFFSET 값으로 업데이트합니다.
     *
     * @param query SQL 쿼리
     * @param limitValue 제한 값
     * @return 업데이트된 쿼리 문자열
     */
    public String pagination(String query, Integer limitValue) {
        try {
            log.info("[query] pagination API 호출 시작");
            log.info("[query] 원본 쿼리: {}", query);
            log.info("[query] 제한 값: {}", limitValue);

            // 요청 데이터 구성
            Map<String, Object> requestData = new HashMap<>();
            requestData.put("query", query);
            requestData.put("limit_value", limitValue);

            log.info("[query] 요청 데이터: {}", requestData);

            // HTTP 헤더 설정
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            // HTTP 요청 생성
            HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestData, headers);

            // API 호출
            String apiUrl = QUERY_API_BASE_URL + "/pagination/pagination";
            log.info("[query] API URL: {}", apiUrl);
            
            ResponseEntity<String> response = restTemplate.postForEntity(apiUrl, request, String.class);

            log.info("[query] API 응답 상태 코드: {}", response.getStatusCode());
            log.info("[query] API 응답 본문: {}", response.getBody());

            if (response.getStatusCode().is2xxSuccessful()) {
                String result = response.getBody();
                log.info("[query] pagination API 호출 성공 - 결과: {}", result);
                
                // JSON 응답에서 result 필드 추출
                if (result != null && !result.trim().isEmpty()) {
                    try {
                        ObjectMapper objectMapper = new ObjectMapper();
                        JsonNode jsonNode = objectMapper.readTree(result);
                        String sqlQuery = jsonNode.get("result").asText();
                        
                        log.info("[query] 추출된 SQL 쿼리: {}", sqlQuery);
                        return sqlQuery;
                    } catch (Exception e) {
                        log.error("[query] JSON 파싱 중 오류: {}", e.getMessage(), e);
                        return query; // 오류 발생 시 원본 쿼리 반환
                    }
                } else {
                    return query;
                }
            } else {
                log.error("[query] pagination API 호출 실패 - 상태 코드: {}", response.getStatusCode());
                return "페이지네이션 처리 중 오류가 발생했습니다.";
            }

        } catch (Exception e) {
            log.error("[query] pagination API 호출 중 예외 발생: {}", e.getMessage(), e);
            return "페이지네이션 처리 중 오류가 발생했습니다: " + e.getMessage();
        }
    }

    /**
     * SQL 쿼리에 ORDER BY절을 추가합니다.
     *
     * @param query SQL 쿼리
     * @return ORDER BY절이 추가된 쿼리 문자열
     */
    public String addOrderBy(String query) {
        try {
            log.info("[query] add_order_by API 호출 - 쿼리: {}", query);

            // 요청 데이터 구성
            Map<String, Object> requestData = new HashMap<>();
            requestData.put("query", query);

            // HTTP 헤더 설정
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            // HTTP 요청 생성
            HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestData, headers);

            // API 호출
            ResponseEntity<String> response = restTemplate.postForEntity(
                QUERY_API_BASE_URL + "/orderby/add_order_by", request, String.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                String result = response.getBody();
                log.info("[query] add_order_by API 호출 성공 - 결과: {}", result);
                
                // JSON 응답에서 result 필드 추출
                if (result != null && !result.trim().isEmpty()) {
                    try {
                        ObjectMapper objectMapper = new ObjectMapper();
                        JsonNode jsonNode = objectMapper.readTree(result);
                        String sqlQuery = jsonNode.get("result").asText();
                        
                        log.info("[query] 추출된 SQL 쿼리: {}", sqlQuery);
                        return sqlQuery;
                    } catch (Exception e) {
                        log.error("[query] JSON 파싱 중 오류: {}", e.getMessage(), e);
                        return query; // 오류 발생 시 원본 쿼리 반환
                    }
                } else {
                    return query;
                }
            } else {
                log.error("[query] add_order_by API 호출 실패 - 상태 코드: {}", response.getStatusCode());
                return "ORDER BY 추가 중 오류가 발생했습니다.";
            }

        } catch (Exception e) {
            log.error("[query] add_order_by API 호출 중 예외 발생: {}", e.getMessage(), e);
            return "ORDER BY 추가 중 오류가 발생했습니다: " + e.getMessage();
        }
    }
}
