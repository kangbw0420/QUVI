package com.daquv.agent.workflow.semanticquery.node;

import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.util.WebSocketUtils;
import com.daquv.agent.workflow.semanticquery.SemanticEntity;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowNode;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState;
import com.daquv.agent.workflow.semanticquery.utils.FileUtils;
import com.daquv.agent.workflow.semanticquery.utils.ResponseParser;
import com.daquv.agent.workflow.semanticquery.utils.YamlUtils;
import com.daquv.agent.workflow.util.LLMRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class ExtractMetricsNode implements SemanticQueryWorkflowNode {

    private final LLMRequest llmRequest;
    private final ResponseParser responseParser;
    private final FileUtils fileUtils;
    private final YamlUtils yamlUtils;
    private final WebSocketUtils webSocketUtils;
    private final RequestProfiler requestProfiler;

    private static final String[] ENTITIES = SemanticEntity.getValues();

    private String extractMetricsAndGroupByPrompt;
    private List<Map<String, Object>> semanticModelYamls = new ArrayList<>();
    private Map<String, List<Map<String, Object>>> metricsDict = new HashMap<>();
    private List<Map<String, Object>> metricsList = new ArrayList<>();
    private Map<String, Map<String, Object>> semanticModelsDict = new HashMap<>();
    private List<Map<String, Object>> semanticModelsList = new ArrayList<>();
    private List<String> noMeasureEntities = new ArrayList<>();

    private String metricsStr;
    private String dimensionStr;
    private String aggregateTimeDimensionsPrompt;

    @PostConstruct
    public void init() {
        log.info("Initializing ExtractMetricsNode...");

        try {
            loadStaticFiles();
            log.info("Static files loaded successfully");

            loadSemanticModels();
            log.info("Semantic models loaded successfully. Total entities: {}, Total metrics: {}",
                    ENTITIES.length, metricsList.size());

            buildStrings();
            log.info("Strings built successfully");


            log.info("ExtractMetricsNode initialization completed successfully");
        } catch (Exception e) {
            log.error("Failed to initialize ExtractMetricsNode", e);
            throw e;
        }
    }

    @Override
    public String getId() {
        return "extract_metrics";
    }

    @Override
    public void execute(SemanticQueryWorkflowState state) {
        String userQuestion = state.getUserQuestion();
        String workflowId = state.getWorkflowId();
        
        // 날짜 정보 생성 (매번 최신 날짜 사용)
        String[] dateStrings = createDateStrings();
        String todayStr = dateStrings[0];
        String yesterdayStr = dateStrings[1];
        String thirtyDaysAgoStr = dateStrings[2];
        
        log.info("Starting metrics and group by extraction for user question: '{}'", userQuestion);
        log.debug("Date strings: today={}, yesterday={}, thirtyDaysAgo={}", todayStr, yesterdayStr, thirtyDaysAgoStr);

        try {
            // SemanticQueryExecution이 없으면 생성
            if (state.getSemanticQueryExecutionMap() == null) {
                state.setSemanticQueryExecutionMap(new HashMap<>());
            }

            // 메트릭과 그룹바이 추출
            long startTime = System.currentTimeMillis();
            Map<String, SemanticQueryWorkflowState.DSL> dslMap = extractMetricsAndGroupBy(userQuestion);
            long endTime = System.currentTimeMillis();
            
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordLlmCall(workflowId, elapsedTime, "extract_metrics");
            
            log.info("Extracted DSLs for {} entities: {}", dslMap.size(), dslMap.keySet());

            // 각 entity별로 SemanticQueryExecution 생성 및 DSL 설정
            for (Map.Entry<String, SemanticQueryWorkflowState.DSL> entry : dslMap.entrySet()) {
                String entity = entry.getKey();
                SemanticQueryWorkflowState.DSL dsl = entry.getValue();
                
                Map<String, SemanticQueryWorkflowState.DSL> entityDslMap = new HashMap<>();
                entityDslMap.put(entity, dsl);
                SemanticQueryWorkflowState.SemanticQueryExecution execution = 
                    SemanticQueryWorkflowState.SemanticQueryExecution.builder()
                        .dsl(entityDslMap)
                        .build();
                
                state.getSemanticQueryExecutionMap().put(entity, execution);
                log.debug("Created SemanticQueryExecution for entity '{}' with {} metrics and {} group by items",
                        entity, dsl.getMetrics().size(), dsl.getGroupBy().size());
            }

            // WebSocket 메시지 전송
            Map<String, Object> data = new HashMap<>();
            data.put("extracted_entities", dslMap.keySet());
            data.put("total_entities", dslMap.size());
            webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "extract_metrics", data);
            
            log.info("Metrics and group by extraction completed successfully. Total entities: {}", dslMap.size());

        } catch (Exception e) {
            log.error("Failed to extract metrics and group by for question: '{}'", userQuestion, e);
            throw e;
        }
    }

    private Map<String, SemanticQueryWorkflowState.DSL> extractMetricsAndGroupBy(String userInput) {
        log.debug("Extracting metrics and group by from user input");

        String prompt = extractMetricsAndGroupByPrompt
                .replace("{entities}", String.join(", ", ENTITIES))
                .replace("{metrics}", metricsStr)
                .replace("{dimensions}", dimensionStr)
                .replace("{time_dimensions}", aggregateTimeDimensionsPrompt);

        log.debug("Calling LLM for metrics and group by extraction");
        String response = llmRequest.callQwenLlm(prompt, userInput);
        log.debug("LLM response received, length: {} characters", response.length());

        Map<String, Object> rawDict = responseParser.parseResponse(response);
        Map<String, SemanticQueryWorkflowState.DSL> result = new HashMap<>();

        for (Map.Entry<String, Object> entry : rawDict.entrySet()) {
            String entity = entry.getKey();
            Map<String, Object> dslData = (Map<String, Object>) entry.getValue();

            if (dslData.containsKey("metrics")) {
                SemanticQueryWorkflowState.DSL dsl = new SemanticQueryWorkflowState.DSL();
                List<String> metrics = (List<String>) dslData.getOrDefault("metrics", new ArrayList<>());
                List<String> groupBy = (List<String>) dslData.getOrDefault("group_by", new ArrayList<>());

                dsl.setMetrics(metrics);
                dsl.setGroupBy(groupBy);
                dsl.setFilters(new ArrayList<>());
                dsl.setOrderBy(new ArrayList<>());
                dsl.setLimit(null);

                result.put(entity, dsl);
                log.debug("Created DSL for entity '{}' with {} metrics and {} group by items",
                        entity, metrics.size(), groupBy.size());
            }
        }

        log.info("Metrics and group by extraction completed. Found {} valid entities", result.size());
        return result;
    }

    // ##########################
    // #      초기화 함수들       #
    // ##########################
    private void loadStaticFiles() {
        log.debug("Loading static prompt files");

        try {
            extractMetricsAndGroupByPrompt = fileUtils.loadFile("prompts/extract_metrics_and_group_by.system");
            log.debug("Loaded extract_metrics_and_group_by.system prompt");

        } catch (Exception e) {
            log.error("Failed to load static files", e);
            throw e;
        }
    }

    private void loadSemanticModels() {
        log.debug("Loading semantic models for {} entities", ENTITIES.length);

        for (String entity : ENTITIES) {
            try {
                log.debug("Loading semantic model for entity: '{}'", entity);
                Map<String, Object> smYaml = yamlUtils.loadYaml(String.format("dbt/models/semantic_models/%s.yml", entity));
                semanticModelYamls.add(smYaml);

                List<Map<String, Object>> metrics = (List<Map<String, Object>>) smYaml.getOrDefault("metrics", new ArrayList<>());
                metricsDict.put(entity, metrics);
                metricsList.addAll(metrics);
                log.debug("Loaded {} metrics for entity '{}'", metrics.size(), entity);

                List<Map<String, Object>> semanticModels = (List<Map<String, Object>>) smYaml.getOrDefault("dbt/models/semantic_models", new ArrayList<>());
                if (!semanticModels.isEmpty()) {
                    Map<String, Object> firstModel = semanticModels.get(0);
                    semanticModelsDict.put(entity, firstModel);
                    semanticModelsList.add(firstModel);
                    log.debug("Loaded semantic model for entity '{}'", entity);
                } else {
                    log.warn("No semantic models found for entity '{}'", entity);
                }

            } catch (Exception e) {
                log.error("Failed to load semantic model for entity '{}'", entity, e);
                throw e;
            }
        }

        noMeasureEntities = new ArrayList<>();
        for (Map<String, Object> sm : semanticModelsList) {
            if (!sm.containsKey("measures") || ((List<?>) sm.get("measures")).isEmpty()) {
                noMeasureEntities.add((String) sm.get("name"));
            }
        }

        log.debug("Found {} entities without measures: {}", noMeasureEntities.size(), noMeasureEntities);
    }

    private void buildStrings() {
        log.debug("Building metrics, dimensions, and time dimensions strings");

        // METRICS_STR 빌드
        StringBuilder metricsBuilder = new StringBuilder();
        for (Map<String, Object> metric : metricsList) {
            metricsBuilder.append(String.format("- %s: %s\n",
                    metric.get("name"),
                    metric.get("description")));
        }
        metricsStr = metricsBuilder.toString();
        log.debug("Built metrics string with {} metrics", metricsList.size());

        // DIMENSION_STR 빌드
        StringBuilder dimensionBuilder = new StringBuilder();
        int totalDimensions = 0;
        for (Map<String, Object> sm : semanticModelsList) {
            dimensionBuilder.append(String.format("## entity: %s\n", sm.get("name")));
            List<Map<String, Object>> dimensions = (List<Map<String, Object>>) sm.getOrDefault("dimensions", new ArrayList<>());
            for (Map<String, Object> dimension : dimensions) {
                dimensionBuilder.append(String.format("- %s__%s: %s\n",
                        sm.get("name"),
                        dimension.get("name"),
                        dimension.getOrDefault("description", "")));
                totalDimensions++;
            }
        }
        dimensionStr = dimensionBuilder.toString();
        log.debug("Built dimensions string with {} total dimensions", totalDimensions);

        // AGGREGATE_TIME_DIMENSIONS_PROMPT 빌드
        StringBuilder timeBuilder = new StringBuilder();
        int timeEntitiesCount = 0;
        for (Map<String, Object> sm : semanticModelsList) {
            Map<String, Object> defaults = (Map<String, Object>) sm.getOrDefault("defaults", new HashMap<>());
            String aggTimeDim = (String) defaults.get("agg_time_dimension");
            if (aggTimeDim != null) {
                timeBuilder.append(String.format("entity %s의 기본 시간값 dimension: %s\n",
                        sm.get("name"), aggTimeDim));
                timeEntitiesCount++;
            }
        }
        aggregateTimeDimensionsPrompt = timeBuilder.toString();
        log.debug("Built time dimensions string with {} entities having time dimensions", timeEntitiesCount);
    }

    private String[] createDateStrings() {
        log.debug("Initializing date strings");

        LocalDate today = LocalDate.now();
        LocalDate yesterday = today.minusDays(1);
        LocalDate thirtyDaysAgo = today.minusDays(30);

        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyyMMdd");
        String todayStr = today.format(formatter);
        String yesterdayStr = yesterday.format(formatter);
        String thirtyDaysAgoStr = thirtyDaysAgo.format(formatter);

        log.debug("Date strings initialized: today={}, yesterday={}, thirtyDaysAgo={}",
                todayStr, yesterdayStr, thirtyDaysAgoStr);
        
        return new String[]{todayStr, yesterdayStr, thirtyDaysAgoStr};
    }
}