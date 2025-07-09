package com.daquv.agent.quvi.requests;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

@Component
public class FstringRequest {
    
    private static final Logger log = LoggerFactory.getLogger(FstringRequest.class);

    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();
    private static final String FSTRING_API_URL = "http://localhost:8105/fstring/compute_fstring";

    /**
     * f-string 템플릿을 외부 API를 통해 계산하고 결과를 반환합니다.
     *
     * @param fstring f-string 템플릿 문자열
     * @param data 템플릿에 사용할 데이터 (List<Map<String, Object>> 또는 다른 타입)
     * @return 계산 결과가 반영된 문자열
     */
    public String computeFString(String fstring, Object data) {
        try {
            log.info("[fstring] 외부 API 호출 - 템플릿: {}, 데이터 타입: {}", 
                    fstring, data.getClass().getSimpleName());

            // 요청 데이터 구성
            Map<String, Object> requestData = new HashMap<>();
            requestData.put("fstring", fstring);
            requestData.put("data", data);

            // HTTP 헤더 설정
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            // HTTP 요청 생성
            HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestData, headers);

            // API 호출
            ResponseEntity<String> response = restTemplate.postForEntity(FSTRING_API_URL, request, String.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                String result = response.getBody();
                log.info("[fstring] API 호출 성공 - 결과: {}", result);
                return parseFstringResponse(result);
            } else {
                log.error("[fstring] API 호출 실패 - 상태 코드: {}", response.getStatusCode());
                return "f-string 처리 중 오류가 발생했습니다.";
            }

        } catch (Exception e) {
            log.error("[fstring] API 호출 중 예외 발생: {}", e.getMessage(), e);
            return "f-string 처리 중 오류가 발생했습니다: " + e.getMessage();
        }
    }

    /**
     * f-string API 응답을 파싱하여 result 필드만 추출합니다.
     *
     * @param response f-string API 응답 문자열
     * @return 파싱된 결과 문자열
     */
    private String parseFstringResponse(String response) {
        if (response == null || response.trim().isEmpty()) {
            return "";
        }

        try {
            JsonNode jsonNode = objectMapper.readTree(response);
            
            // success 필드 확인
            if (jsonNode.has("success") && jsonNode.get("success").asBoolean()) {
                // result 필드가 있으면 반환
                if (jsonNode.has("result")) {
                    String result = jsonNode.get("result").asText();
                    log.info("[fstring] 파싱된 결과: {}", result);
                    return result;
                } else {
                    log.warn("[fstring] success가 true이지만 result 필드가 없습니다: {}", response);
                    return "";
                }
            } else {
                log.warn("[fstring] success가 false이거나 없습니다: {}", response);
                return "";
            }
            
        } catch (Exception e) {
            log.error("[fstring] JSON 파싱 중 오류: {}", e.getMessage(), e);
            // JSON 파싱에 실패하면 원본 응답을 그대로 반환
            return response;
        }
    }
}