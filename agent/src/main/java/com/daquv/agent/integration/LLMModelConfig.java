package com.daquv.agent.integration;

import org.springframework.stereotype.Component;
import java.util.HashMap;
import java.util.Map;

@Component
public class LLMModelConfig {
    
    // 모델 타입별 분류 (vLLM vs API)
    private final Map<String, ModelType> modelTypeMapping;
    
    // 노드별 LLM 매핑(소문자만 사용)
    private final Map<String, String> nodeModelMapping;
    
    // 기본 모델
    private final String defaultModel = "qwen_low";
    
    public LLMModelConfig() {
        modelTypeMapping = new HashMap<>();
        nodeModelMapping = new HashMap<>();
        
        // vLLM 모델들
        modelTypeMapping.put("qwen_low", ModelType.VLLM);
        modelTypeMapping.put("qwen_high", ModelType.VLLM);
        modelTypeMapping.put("qwen_boolean", ModelType.VLLM);
        modelTypeMapping.put("selector", ModelType.VLLM);
        modelTypeMapping.put("nl2sql", ModelType.VLLM);
        modelTypeMapping.put("solver", ModelType.VLLM);
        
        // API 모델들
        modelTypeMapping.put("gemini", ModelType.API);

        // 노드별 LLM 매핑(소문자만 사용)
        nodeModelMapping.put("classifyjoynode", "qwen_low");
        nodeModelMapping.put("killjoynode", "qwen_low");
        
        nodeModelMapping.put("nextpagenode", "qwen_low");
        nodeModelMapping.put("splitquestionnode", "qwen_low");
        
        nodeModelMapping.put("datecheckernode", "qwen_low");
        
        nodeModelMapping.put("extractmetricsnode", "qwen_low");
        nodeModelMapping.put("extractfilternode", "qwen_low");
        nodeModelMapping.put("manipulationnode", "qwen_low");
        nodeModelMapping.put("dsl2sqlnode", "qwen_low");
        
        nodeModelMapping.put("postprocessnode", "qwen_low");
        nodeModelMapping.put("responsednode", "qwen_low");
        nodeModelMapping.put("nodata", "qwen_low");
    }
    
    public ModelType getModelType(String modelType) {
        return modelTypeMapping.get(modelType);
    }
    
    public String getNodeModelMapping(String nodeName) {
        return nodeModelMapping.get(nodeName);
    }
    
    public String getDefaultModel() {
        return defaultModel;
    }
    
    public enum ModelType {
        VLLM,
        API
    }
}
