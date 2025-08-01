package com.daquv.agent.requests;

import com.daquv.agent.workflow.dto.MetricFlowRequestDto;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@RequiredArgsConstructor
@Component
public class Dsl2sqlRequest {

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    @Value("${api.quvi-base-url}")
    private String pythonServerUrl;

    private String dsl2sqlEndpoint = "/dsl2sql/generate-sql";

    public Map<String, String> generateSqlFromDsl(Map<String, MetricFlowRequestDto> requests) {
        try {
            String url = pythonServerUrl + dsl2sqlEndpoint;

            // HTTP 헤더 설정
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            // semantic_manifest.json 내용 추출
            ClassPathResource resource = new ClassPathResource("dbt/semantic_manifest.json");
            StringBuilder manifestContentBuilder = new StringBuilder();

            try (InputStream is = resource.getInputStream();
                 BufferedReader reader = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    manifestContentBuilder.append(line).append("\n");
                }
            } catch (IOException e) {
                log.error("Failed to read semantic_manifest.json", e);
                return createErrorResponse("Failed to read semantic_manifest.json: " + e.getMessage());
            }

            String manifestContent = manifestContentBuilder.toString();

            // Python DTO 구조에 맞게 요청 데이터 래핑
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("requests", requests);
            requestBody.put("manifest_content", manifestContent);

            // HTTP 요청 생성
            HttpEntity<Map<String, Object>> requestEntity = new HttpEntity<>(requestBody, headers);

            log.info("Sending batch MetricFlow request to Python server: {}", url);
            log.debug("Request body: {}", requestBody);

            // Python 서버로 요청 전송
            ResponseEntity<String> response = restTemplate.exchange(
                    url,
                    HttpMethod.POST,
                    requestEntity,
                    String.class
            );

            if (response.getStatusCode() == HttpStatus.OK) {
                // 응답을 Map으로 파싱
                Map<String, Object> responseMap = objectMapper.readValue(
                        response.getBody(),
                        new TypeReference<Map<String, Object>>() {}
                );

                Boolean success = (Boolean) responseMap.get("success");
                if (Boolean.TRUE.equals(success)) {
                    log.info("Successfully received SQL from Python server");
                    @SuppressWarnings("unchecked")
                    Map<String, String> results = (Map<String, String>) responseMap.get("results");

                    if (results != null) {
                        for (Map.Entry<String, String> entry : results.entrySet()) {
                            String key = entry.getKey();
                            String value = entry.getValue();
                            log.info("Result - {}: {}", key, value);
                        }
                    }

                    return results != null ? results : new HashMap<>();
                } else {
                    String error = (String) responseMap.get("error");
                    log.error("Python server returned error: {}", error);
                    return createErrorResponse(error);
                }
            } else {
                log.error("Python server returned non-OK status: {}", response.getStatusCode());
                return createErrorResponse("Python server returned status: " + response.getStatusCode());
            }

        } catch (Exception e) {
            log.error("Failed to communicate with Python MetricFlow server", e);
            return createErrorResponse("Communication error: " + e.getMessage());
        }
    }

    private Map<String, String> createErrorResponse(String errorMessage) {
        Map<String, String> errorResponse = new HashMap<>();
        errorResponse.put("error", errorMessage != null ? errorMessage : "Unknown error");
        return errorResponse;
    }
}