package com.daquv.agent.workflow.util;

import com.daquv.agent.quvi.llmadmin.GenerationService;
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

    @Value("${llm.base-url}")
    private String baseUrl;
    
    @Autowired
    private GenerationService generationService;
    
    @Autowired
    private RequestProfiler profiler;
    
    private final RestTemplate restTemplate = new RestTemplate();
    
    // 모델별 설정 (간단한 맵으로 관리)
    private final Map<String, ModelConfig> modelConfigs;

    public LLMRequest() {
        modelConfigs = new HashMap<>();
        modelConfigs.put("qwen_llm", new ModelConfig("Qwen/Qwen2.5-Coder-14B-Instruct-AWQ", 0.01, 1000));
        modelConfigs.put("qwen_high", new ModelConfig("Qwen/Qwen2.5-Coder-14B-Instruct-AWQ", 0.7, 1000));
        modelConfigs.put("qwen_boolean", new ModelConfig("Qwen/Qwen2.5-Coder-14B-Instruct-AWQ", 0.01, 1));
        modelConfigs.put("selector", new ModelConfig("selector", 0.01, 300));
        modelConfigs.put("nl2sql", new ModelConfig("nl2sql", 0.01, 3000));
        modelConfigs.put("solver", new ModelConfig("solver", 0.1, 1000));
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
                generationService.updateQuestion(qnaId, prompt, config.getModelName());
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
                String nodeId = determineNodeIdFromStackTrace();
                profiler.recordLlmCall(chainId, elapsedTime, nodeId);
                log.info("LLM 프로파일링 기록 완료 - chainId: {}, elapsedTime: {}s", chainId, elapsedTime);
            } else {
                log.debug("LLM 프로파일링 기록 스킵 - chainId가 null임");
            }
            
            String content = extractContent(response);
            
            // QnA ID가 있으면 답변 기록
            if (qnaId != null) {
                generationService.recordAnswer(qnaId, content, null);
            }
            
            return content;
            
        } catch (Exception e) {
            log.error("LLM 호출 실패: {}", e.getMessage(), e);
            throw new RuntimeException("LLM 호출 실패: " + e.getMessage());
        }
    }
    
    // 편의 메서드들
    public String callQwenLlm(String prompt) {
        return callModel("qwen_llm", prompt);
    }

    public String callQwenLlm(String prompt, String qnaId) {
        return callModel("qwen_llm", prompt, qnaId);
    }

    public String callQwenLlm(String prompt, String qnaId, String chainId) {
        return callModel("qwen_llm", prompt, qnaId, chainId);
    }

    public String callQwenHigh(String prompt) {
        return callModel("qwen_high", prompt);
    }

    public String callQwenHigh(String prompt, String qnaId) {
        return callModel("qwen_high", prompt, qnaId);
    }

    public String callQwenHigh(String prompt, String qnaId, String chainId) {
        return callModel("qwen_high", prompt, qnaId, chainId);
    }

    public String callQwenBoolean(String prompt) {
        return callModel("qwen_boolean", prompt);
    }

    public String callQwenBoolean(String prompt, String qnaId) {
        return callModel("qwen_boolean", prompt, qnaId);
    }

    public String callQwenBoolean(String prompt, String qnaId, String chainId) {
        return callModel("qwen_boolean", prompt, qnaId, chainId);
    }

    public String callSelector(String prompt) {
        return callModel("selector", prompt);
    }

    public String callSelector(String prompt, String qnaId) {
        return callModel("selector", prompt, qnaId);
    }

    public String callSelector(String prompt, String qnaId, String chainId) {
        return callModel("selector", prompt, qnaId, chainId);
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

    public String callSolver(String prompt, String qnaId, String chainId) {
        return callModel("solver", prompt, qnaId, chainId);
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
    private String determineNodeIdFromStackTrace() {
        StackTraceElement[] stackTrace = Thread.currentThread().getStackTrace();

        for (StackTraceElement element : stackTrace) {
            String className = element.getClassName();

            if (className.contains("CheckpointNode")) return "checkpoint";
            if (className.contains("CommanderNode")) return "commander";
            if (className.contains("Nl2sqlNode")) return "nl2sql";
            if (className.contains("SafeguardNode")) return "safeguard";
            if (className.contains("RespondentNode")) return "respondent";
            if (className.contains("NodataNode")) return "nodata";
            if (className.contains("KilljoyNode")) return "killjoy";
        }

        return "llm_service";
    }
} 