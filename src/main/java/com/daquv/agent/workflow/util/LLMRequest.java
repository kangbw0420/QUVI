package com.daquv.agent.workflow.util;

import com.daquv.agent.quvi.llmadmin.QnaService;
import com.daquv.agent.quvi.util.RequestProfiler;
import lombok.Data;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class LLMRequest {
    
    private static final Logger log = LoggerFactory.getLogger(LLMRequest.class);
    
    @Value("${llm.base-url:http://121.78.145.49:8001}")
    private String baseUrl;
    
    @Autowired
    private QnaService qnaService;
    
    @Autowired
    private RequestProfiler profiler;
    
    private final RestTemplate restTemplate = new RestTemplate();
    
    // 모델별 설정 (간단한 맵으로 관리)
    private final Map<String, ModelConfig> modelConfigs;

    public LLMRequest() {
        modelConfigs = new HashMap<>();
        modelConfigs.put("selector", new ModelConfig("selector", 0.01, 300));
        modelConfigs.put("nl2sql", new ModelConfig("nl2sql", 0.01, 3000));
        modelConfigs.put("solver", new ModelConfig("solver", 0.1, 1000));
        modelConfigs.put("devstral", new ModelConfig("unsloth/Devstral-Small-2505-bnb-4bit", 0.01, 1000));
        modelConfigs.put("devstral-high", new ModelConfig("unsloth/Devstral-Small-2505-bnb-4bit", 0.7, 1000));
    }
    
    public String callModel(String modelType, String prompt) {
        return callModel(modelType, prompt, null);
    }
    
    public String callModel(String modelType, String prompt, String qnaId) {
        return callModel(modelType, prompt, qnaId, null);
    }
    
    public String callModel(String modelType, String prompt, String qnaId, String chainId) {
        ModelConfig config = modelConfigs.get(modelType);
        if (config == null) {
            throw new IllegalArgumentException("Unknown model type: " + modelType);
        }
        
        try {
            log.info("Calling {} model with prompt length: {}", config.modelName, prompt.length());
            log.info("prompt: {}", prompt);

            Map<String, Object> messageMap = new HashMap<>();
            messageMap.put("role", "user");
            messageMap.put("content", prompt);

            List<Map<String, Object>> messages = new ArrayList<>();
            messages.add(messageMap);
            
           // QnA ID가 있으면 질문 업데이트
            if (qnaId != null) {
                qnaService.updateQuestion(qnaId, prompt, config.getModelName());
            }
            Map<String, Object> request = new HashMap<>();
            request.put("model", config.modelName);
            request.put("messages", messages);
            request.put("temperature", config.temperature);
            request.put("max_tokens", config.maxTokens);
    
            
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            
            long startTime = System.currentTimeMillis();
            
            ResponseEntity<Map> response = restTemplate.postForEntity(
                baseUrl + "/v1/chat/completions",
                new HttpEntity<>(request, headers),
                Map.class
            );
            
            // 프로파일링 기록
            double elapsedTime = (System.currentTimeMillis() - startTime) / 1000.0;
            if (chainId != null) {
                profiler.recordLlmCall(chainId, elapsedTime);
                log.info("LLM 프로파일링 기록 완료 - chainId: {}, elapsedTime: {}s", chainId, elapsedTime);
            } else {
                log.debug("LLM 프로파일링 기록 스킵 - chainId가 null임");
            }
            
            String content = extractContent(response);
            
            // QnA ID가 있으면 답변 기록
            if (qnaId != null) {
                qnaService.recordAnswer(qnaId, content, null);
            }
            
            return content;
            
        } catch (Exception e) {
            log.error("LLM 호출 실패: {}", e.getMessage(), e);
            throw new RuntimeException("LLM 호출 실패: " + e.getMessage());
        }
    }
    
    // 편의 메서드들
    public String callSelector(String prompt) {
        return callModel("selector", prompt);
    }
    
    public String callSelector(String prompt, String qnaId) {
        return callModel("selector", prompt, qnaId);
    }
    
    public String callNl2sql(String prompt) {
        return callModel("nl2sql", prompt);
    }
    
    public String callNl2sql(String prompt, String qnaId) {
        return callModel("nl2sql", prompt, qnaId);
    }
    
    public String callNl2sql(String prompt, String qnaId, String chainId) {
        return callModel("nl2sql", prompt, qnaId, chainId);
    }
    
    public String callSolver(String prompt) {
        return callModel("solver", prompt);
    }
    
    public String callSolver(String prompt, String qnaId) {
        return callModel("solver", prompt, qnaId);
    }
    
    public String callDevstral(String prompt) {
        return callModel("devstral", prompt);
    }
    
    public String callDevstral(String prompt, String qnaId) {
        return callModel("devstral", prompt, qnaId);
    }
    
    public String callDevstral(String prompt, String qnaId, String chainId) {
        return callModel("devstral", prompt, qnaId, chainId);
    }
    
    public String callDevstralHigh(String prompt) {
        return callModel("devstral-high", prompt);
    }
    
    public String callDevstralHigh(String prompt, String qnaId) {
        return callModel("devstral-high", prompt, qnaId);
    }
    
    /**
     * SQL 쿼리를 수정합니다 (Safeguard용).
     * 
     * @param sqlQuery 원본 SQL 쿼리
     * @param sqlError SQL 에러 메시지
     * @param traceId 현재 trace ID
     * @return 수정된 SQL 쿼리
     */
    public String modifyQuery(String sqlQuery, String sqlError, String traceId) {
        try {
            log.info("SQL 쿼리 수정 시작 - 원본 쿼리: {}, 에러: {}, traceId: {}", sqlQuery, sqlError, traceId);
            
            // QnA ID 생성 (올바른 trace ID 사용)
            String qnaId = qnaService.createQnaId(traceId);
            
            // Safeguard 프롬프트 생성
            String prompt = String.format(
                "다음 SQL 쿼리에 오류가 있습니다. 오류를 수정하여 올바른 SQL 쿼리를 생성해주세요.\n\n" +
                "원본 쿼리: %s\n" +
                "오류 메시지: %s\n\n" +
                "수정된 SQL 쿼리만 반환해주세요. 다른 설명은 포함하지 마세요.",
                sqlQuery, sqlError
            );
            
            // LLM 호출
            String response = callDevstral(prompt, qnaId);
            
            // SQL 쿼리 추출
            String modifiedQuery = extractSqlQuery(response);
            
            log.info("SQL 쿼리 수정 완료 - 수정된 쿼리: {}", modifiedQuery);
            
            return modifiedQuery;
            
        } catch (Exception e) {
            log.error("SQL 쿼리 수정 중 오류 발생: {}", e.getMessage(), e);
            return sqlQuery; // 오류 발생 시 원본 쿼리 반환
        }
    }
    
    /**
     * LLM 응답에서 SQL 쿼리를 추출합니다.
     */
    private String extractSqlQuery(String response) {
        if (response == null || response.trim().isEmpty()) {
            return "";
        }
        
        // SQL 키워드로 시작하는 부분 찾기
        String[] lines = response.split("\n");
        for (String line : lines) {
            String trimmed = line.trim();
            if (trimmed.toUpperCase().startsWith("SELECT") || 
                trimmed.toUpperCase().startsWith("WITH") ||
                trimmed.toUpperCase().startsWith("INSERT") ||
                trimmed.toUpperCase().startsWith("UPDATE") ||
                trimmed.toUpperCase().startsWith("DELETE")) {
                return trimmed;
            }
        }
        
        // SQL 키워드가 없으면 전체 응답 반환
        return response.trim();
    }
    
    private String extractContent(ResponseEntity<Map> response) {
        Map<String, Object> body = response.getBody();
        if (body == null) {
            throw new RuntimeException("API 응답이 비어있습니다");
        }
        
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> choices = (List<Map<String, Object>>) body.get("choices");
        if (choices == null || choices.isEmpty()) {
            throw new RuntimeException("API 응답에 choices가 없습니다");
        }
        
        @SuppressWarnings("unchecked")
        Map<String, Object> message = (Map<String, Object>) choices.get(0).get("message");
        if (message == null) {
            throw new RuntimeException("API 응답에 message가 없습니다");
        }
        
        String content = (String) message.get("content");
        return content != null ? content.trim() : "";
    }
    
    @Data
    private static class ModelConfig {
        private String modelName;
        private double temperature;
        private int maxTokens;
        
        public ModelConfig(String modelName, double temperature, int maxTokens) {
            this.modelName = modelName;
            this.temperature = temperature;
            this.maxTokens = maxTokens;
        }
        
        public String getModelName() {
            return modelName;
        }
        
        public double getTemperature() {
            return temperature;
        }
        
        public int getMaxTokens() {
            return maxTokens;
        }
    }
} 