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

    // API 모델 상세 설정
    private final Map<String, ApiModelConfig> apiModelConfigs;

    // vLLM 모델 상세 설정
    private final Map<String, VLLMModelConfig> vllmModelConfigs;

    public LLMModelConfig() {
        modelTypeMapping = new HashMap<>();
        nodeModelMapping = new HashMap<>();
        apiModelConfigs = new HashMap<>();
        vllmModelConfigs = new HashMap<>();

        // vLLM 모델들
        modelTypeMapping.put("qwen_low", ModelType.VLLM);
        modelTypeMapping.put("qwen_high", ModelType.VLLM);
        modelTypeMapping.put("qwen_boolean", ModelType.VLLM);
        modelTypeMapping.put("exaone_low", ModelType.VLLM);
        modelTypeMapping.put("exaone_high", ModelType.VLLM);
        modelTypeMapping.put("devstral_local_low", ModelType.VLLM);
        modelTypeMapping.put("devstral_local_high", ModelType.VLLM);
        modelTypeMapping.put("devstral_kjbank_low", ModelType.VLLM);
        modelTypeMapping.put("devstral_kjbank_high", ModelType.VLLM);
        modelTypeMapping.put("selector", ModelType.VLLM);
        modelTypeMapping.put("nl2sql", ModelType.VLLM);
        modelTypeMapping.put("solver", ModelType.VLLM);

        // API 모델들
        // API 모델 상세 설정

        apiModelConfigs.put("gpt5_low_minimal", new ApiModelConfig(
                "gpt5",
                "https://api.openai.com/v1/responses",
                0,
                0,
                ModelProvider.GPT5,
                0,
                "low",
                "minimal"
        ));

        apiModelConfigs.put("gemini_flash_low_0", new ApiModelConfig(
                "gemini-2.5-flash",
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                0.1,
                16384,
                ModelProvider.GEMINI,
                0,
                "",
                ""
        ));
        apiModelConfigs.put("gemini_flash_low_100", new ApiModelConfig(
                "gemini-2.5-flash",
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                0.1,
                16384,
                ModelProvider.GEMINI,
                100,
                "",
                ""
        ));
        apiModelConfigs.put("gemini_flash_low_300", new ApiModelConfig(
                "gemini-2.5-flash",
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                0.1,
                16384,
                ModelProvider.GEMINI,
                300,
                "",
                ""
        ));
        apiModelConfigs.put("gemini_flash_low_500", new ApiModelConfig(
                "gemini-2.5-flash",
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                0.1,
                16384,
                ModelProvider.GEMINI,
                500,
                "",
                ""
        ));
        apiModelConfigs.put("gemini_flash_low_1000", new ApiModelConfig(
                "gemini-2.5-flash",
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                0.1,
                16384,
                ModelProvider.GEMINI,
                1000,
                "",
                ""
        ));
        apiModelConfigs.put("gemini_flash_low_3000", new ApiModelConfig(
                "gemini-2.5-flash",
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                0.1,
                16384,
                ModelProvider.GEMINI,
                3000,
                "",
                ""
        ));

        // 노드별 LLM 매핑(소문자만 사용)
        nodeModelMapping.put("classifyjoynode", "qwen_low");
        nodeModelMapping.put("killjoynode", "qwen_low");

        nodeModelMapping.put("nextpagenode", "qwen_low");
        nodeModelMapping.put("splitquestionnode", "qwen_low");

        nodeModelMapping.put("datecheckernode", "qwen_low");

        nodeModelMapping.put("extractmetricsnode", "qwen_low");
        nodeModelMapping.put("extractfilternode", "qwen_low");
        nodeModelMapping.put("manipulationnode", "qwen_low");

        nodeModelMapping.put("postprocessnode", "qwen_low");
        nodeModelMapping.put("responsednode", "qwen_low");
        nodeModelMapping.put("nodatanode", "qwen_low");

        vllmModelConfigs.put("qwen_low", new VLLMModelConfig("Qwen/Qwen2.5-Coder-14B-Instruct-AWQ", 0.01, 1000));
        vllmModelConfigs.put("exaone_low", new VLLMModelConfig("LGAI-EXAONE/EXAONE-3.5-32B-Instruct-AWQ", 0.01, 1000));
        vllmModelConfigs.put("devstral_local_low", new VLLMModelConfig(
                "/home/daquv/.cache/huggingface/hub/models--unsloth--Devstral-Small-2507-unsloth-bnb-4bit/snapshots/0578b9b52309df8ae455eb860a6cebe50dc891cd",
                0.01, 1000));
        vllmModelConfigs.put("devstral_kjbank_low",
                new VLLMModelConfig("/models/Devstral-Small-2507-unsloth-bnb-4bit", 0.01, 1000));
        vllmModelConfigs.put("qwen_high", new VLLMModelConfig("Qwen/Qwen2.5-Coder-14B-Instruct-AWQ", 0.9, 1000));
        vllmModelConfigs.put("exaone_high", new VLLMModelConfig("LGAI-EXAONE/EXAONE-3.5-32B-Instruct-AWQ", 0.9, 1000));
        vllmModelConfigs.put("devstral_local_high", new VLLMModelConfig(
                "/home/daquv/.cache/huggingface/hub/models--unsloth--Devstral-Small-2507-unsloth-bnb-4bit/snapshots/0578b9b52309df8ae455eb860a6cebe50dc891cd",
                0.9, 1000));
        vllmModelConfigs.put("devstral_kjbank_high",
                new VLLMModelConfig("/models/Devstral-Small-2507-unsloth-bnb-4bit", 0.9, 1000));
        vllmModelConfigs.put("selector", new VLLMModelConfig("selector", 0.01, 300));
        vllmModelConfigs.put("nl2sql", new VLLMModelConfig("nl2sql", 0.01, 3000));
        vllmModelConfigs.put("solver", new VLLMModelConfig("solver", 0.1, 1000));
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

    public ApiModelConfig getApiModelConfig(String modelType) {
        return apiModelConfigs.get(modelType);
    }

    public VLLMModelConfig getVLLMModelConfig(String modelType) {
        return vllmModelConfigs.get(modelType);
    }

    public enum ModelType {
        VLLM,
        API
    }

    public enum ModelProvider {
        GEMINI,
        GPT5
    }

    public static class ApiModelConfig {
        private final String modelName;
        private final String endpoint;
        private final double temperature;
        private final int maxTokens;
        private final ModelProvider provider;
        private final int thinkingBudget;
        private final String verbosity;
        private final String effort;

        public ApiModelConfig(String modelName, String endpoint, double temperature, int maxTokens, ModelProvider provider, int thinkingBudget, String verbosity, String effort) {
            this.modelName = modelName;
            this.endpoint = endpoint;
            this.temperature = temperature;
            this.maxTokens = maxTokens;
            this.provider = provider;
            this.thinkingBudget = thinkingBudget;
            this.verbosity = verbosity;
            this.effort = effort;
        }

        public String getModelName() { return modelName; }
        public String getEndpoint() { return endpoint; }
        public double getTemperature() { return temperature; }
        public int getMaxTokens() { return maxTokens; }
        public ModelProvider getProvider() { return provider; }
        public int getThinkingBudget() { return thinkingBudget; }
        public String getVerbosity() { return verbosity; }
        public String getEffort() { return effort; }
    }

    public static class VLLMModelConfig {
        private final String modelName;
        private final double temperature;
        private final int maxTokens;

        public VLLMModelConfig(String modelName, double temperature, int maxTokens) {
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
