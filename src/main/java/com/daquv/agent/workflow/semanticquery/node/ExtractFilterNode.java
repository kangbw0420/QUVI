package com.daquv.agent.workflow.semanticquery.node;

import com.daquv.agent.quvi.llmadmin.GenerationService;
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
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Component
@RequiredArgsConstructor
public class ExtractFilterNode implements SemanticQueryWorkflowNode {

    private final LLMRequest llmRequest;
    private final ResponseParser responseParser;
    private final FileUtils fileUtils;
    private final YamlUtils yamlUtils;
    private final WebSocketUtils webSocketUtils;
    private final RequestProfiler requestProfiler;
    private final GenerationService generationService;

    private static final String[] ENTITIES = SemanticEntity.getValues();

    private String extractFiltersPrompt;
    private Map<String, List<Map<String, Object>>> metricsDict = new HashMap<>();
    private List<Map<String, Object>> metricsList = new ArrayList<>();
    private List<Map<String, Object>> semanticModelsList = new ArrayList<>();

    private String dimensionStr;
    private String aggregateTimeDimensionsPrompt;
    private String todayStr;
    private String yesterdayStr;
    private String thirtyDaysAgoStr;

    private static final Set<String> TIME_SUFFIXES;
    static {
        TIME_SUFFIXES = new HashSet<>();
        TIME_SUFFIXES.add("bal__reg_dt");
        TIME_SUFFIXES.add("bal__open_dt");
        TIME_SUFFIXES.add("bal__due_dt");
        TIME_SUFFIXES.add("bal_fore__reg_dt");
        TIME_SUFFIXES.add("bal_fore__open_dt");
        TIME_SUFFIXES.add("bal_fore__due_dt");
        TIME_SUFFIXES.add("trsc__trsc_dt");
        TIME_SUFFIXES.add("trsc_fore__trsc_dt");
    }

    @PostConstruct
    public void init() {
        log.info("Initializing ExtractFilterNode...");

        try {
            loadStaticFiles();
            log.info("Static files loaded successfully");

            loadSemanticModels();
            log.info("Semantic models loaded successfully. Total entities: {}, Total metrics: {}",
                    ENTITIES.length, metricsList.size());

            buildStrings();
            log.info("Strings built successfully");

            log.info("Date strings initialized. Today: {}, Yesterday: {}, 30 days ago: {}",
                    todayStr, yesterdayStr, thirtyDaysAgoStr);

            log.info("ExtractFilterNode initialization completed successfully");
        } catch (Exception e) {
            log.error("Failed to initialize ExtractFilterNode", e);
            throw e;
        }
    }

    @Override
    public String getId() {
        return "extractFilter";
    }

    @Override
    public void execute(SemanticQueryWorkflowState state) {
        String userQuestion = state.getUserQuestion();
        String workflowId = state.getWorkflowId();
        String qnaId = generationService.createQnaId(state.getNodeId());
        
        log.info("Starting filter extraction and application for user question: '{}'", userQuestion);

        try {
            Map<String, SemanticQueryWorkflowState.SemanticQueryExecution> executionMap = 
                state.getSemanticQueryExecutionMap();
            
            if (executionMap == null || executionMap.isEmpty()) {
                log.error("No SemanticQueryExecution found in state. ExtractMetricsNode should run first.");
                throw new IllegalStateException("No SemanticQueryExecution found in state");
            }

            // DSL Map 생성 (필터 추출용)
            Map<String, SemanticQueryWorkflowState.DSL> dslMap = new HashMap<>();
            for (Map.Entry<String, SemanticQueryWorkflowState.SemanticQueryExecution> entry : executionMap.entrySet()) {
                String entity = entry.getKey();
                SemanticQueryWorkflowState.SemanticQueryExecution execution = entry.getValue();
                if (execution.getDsl() != null && execution.getDsl().containsKey(entity)) {
                    dslMap.put(entity, execution.getDsl().get(entity));
                }
            }

            // 필터 추출 및 적용
            long startTime = System.currentTimeMillis();
            // 날짜 정보 생성 (매번 최신 날짜 사용)
            String[] dateStrings = createDateStrings();
            String todayStr = dateStrings[0];
            String yesterdayStr = dateStrings[1];
            String thirtyDaysAgoStr = dateStrings[2];
            log.debug("Date strings: today={}, yesterday={}, thirtyDaysAgo={}", todayStr, yesterdayStr, thirtyDaysAgoStr);
            
            Map<String, List<String>> filtersDict = extractFilters(userQuestion, dslMap, todayStr, yesterdayStr, thirtyDaysAgoStr, qnaId);
            long endTime = System.currentTimeMillis();
            
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordLlmCall(workflowId, elapsedTime, "extract_filter");
            
            log.info("Extracted filters for {} entities", filtersDict.size());

            // 각 entity별로 필터 적용
            int totalFiltersApplied = 0;
            for (Map.Entry<String, List<String>> entry : filtersDict.entrySet()) {
                String entity = entry.getKey();
                List<String> filters = entry.getValue();
                
                if (executionMap.containsKey(entity)) {
                    SemanticQueryWorkflowState.SemanticQueryExecution execution = executionMap.get(entity);
                    SemanticQueryWorkflowState.DSL dsl = execution.getDsl().get(entity);
                    
                    if (dsl != null) {
                        dsl.setFilters(filters);
                        totalFiltersApplied += filters.size();
                        log.debug("Applied {} filters to entity '{}': {}", filters.size(), entity, filters);
                    }
                }
            }

            // WebSocket 메시지 전송
            Map<String, Object> data = new HashMap<>();
            data.put("entities_with_filters", filtersDict.keySet());
            data.put("total_filters_applied", totalFiltersApplied);
            webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "extract_filter", data);
            
            log.info("Filter extraction and application completed successfully. Total filters applied: {}", totalFiltersApplied);

        } catch (Exception e) {
            log.error("Failed to extract and apply filters for question: '{}'", userQuestion, e);
            throw e;
        }
    }

    private Map<String, List<String>> extractFilters(String userInput, Map<String, SemanticQueryWorkflowState.DSL> dslDict, 
                                                      String todayStr, String yesterdayStr, String thirtyDaysAgoStr, String qnaId) {
        log.debug("Extracting filters from user input");

        String dslString = formatDslMapForPrompt(dslDict);
        log.debug("Formatted DSL string for prompt: {}", dslString);

        String systemPrompt = extractFiltersPrompt
                .replace("{entity_ids}", String.join(", ", metricsDict.keySet()))
                .replace("{today}", todayStr)
                .replace("{yesterday}", yesterdayStr)
                .replace("{thirty_days_ago}", thirtyDaysAgoStr)
                .replace("{time_dimensions}", aggregateTimeDimensionsPrompt)
                .replace("{dsl}", dslString)
                .replace("{dimensions}", dimensionStr)
                .replace("{user_input}", userInput);

        log.debug("Calling LLM for filter extraction");
        String response = llmRequest.callQwenLlm(systemPrompt, qnaId);
        log.debug("LLM response received for filters, length: {} characters", response.length());

        Map<String, Object> parsedResponse = responseParser.parseResponse(response);
        Map<String, List<String>> rawFilters = (Map<String, List<String>>) parsedResponse.get("filters");

        Map<String, List<String>> convertedFilters = convertFilterDictToDimensionStrings(rawFilters);
        log.info("Filter extraction completed. Converted {} filter groups", convertedFilters.size());

        return convertedFilters;
    }

    private Map<String, List<String>> convertFilterDictToDimensionStrings(Map<String, List<String>> filterDict) {
        log.debug("Converting filter dictionary to dimension strings");
        Map<String, List<String>> result = new HashMap<>();

        for (Map.Entry<String, List<String>> entry : filterDict.entrySet()) {
            String entityId = entry.getKey();
            List<String> filters = entry.getValue();
            List<String> expressions = new ArrayList<>();

            for (String filter : filters) {
                try {
                    String exprStr = convertSingleFilter(filter);
                    expressions.add(exprStr);
                    log.debug("Converted filter '{}' to expression: '{}'", filter, exprStr);
                } catch (Exception e) {
                    log.warn("Failed to convert filter '{}' for entity '{}': {}", filter, entityId, e.getMessage());
                }
            }

            result.put(entityId, expressions);
        }

        log.debug("Filter conversion completed. Processed {} entities", result.size());
        return result;
    }

    private String convertSingleFilter(String filter) {
        log.trace("Converting single filter: '{}'", filter);

        // 정규식으로 필터 파싱
        Pattern pattern = Pattern.compile("\\s*(\\w+)\\s*(=|>=|<=|>|<|!=|like|LIKE|in|IN)\\s*['\"]?(.*?)['\"]?\\s*$",
                Pattern.CASE_INSENSITIVE);
        Matcher matcher = pattern.matcher(filter);

        if (!matcher.matches()) {
            log.error("Invalid filter format: '{}'", filter);
            throw new IllegalArgumentException("Invalid filter format: " + filter);
        }

        String column = matcher.group(1);
        String op = matcher.group(2);
        String value = matcher.group(3);

        String result;
        if (TIME_SUFFIXES.contains(column)) {
            if (op.toLowerCase().matches("in|IN")) {
                if (value.startsWith("(") && value.endsWith(")")) {
                    result = String.format("{{ TimeDimension('%s') }} %s %s", column, op, value);
                } else {
                    result = String.format("{{ TimeDimension('%s') }} %s ('%s')", column, op, value);
                }
            } else {
                result = String.format("{{ TimeDimension('%s') }} %s '%s'", column, op, value);
            }
        } else {
            if (op.toLowerCase().matches("in|IN")) {
                if (value.startsWith("(") && value.endsWith(")")) {
                    result = String.format("{{ Dimension('%s') }} %s %s", column, op, value);
                } else {
                    result = String.format("{{ Dimension('%s') }} %s ('%s')", column, op, value);
                }
            } else {
                result = String.format("{{ Dimension('%s') }} %s '%s'", column, op, value);
            }
        }

        return result;
    }

    private String formatDslMapForPrompt(Map<String, SemanticQueryWorkflowState.DSL> dslMap) {
        if (dslMap == null || dslMap.isEmpty()) {
            return "No DSL entities found.";
        }

        StringBuilder sb = new StringBuilder();
        sb.append("Current DSL Configuration:\n");

        for (Map.Entry<String, SemanticQueryWorkflowState.DSL> entry : dslMap.entrySet()) {
            String entity = entry.getKey();
            SemanticQueryWorkflowState.DSL dsl = entry.getValue();
            sb.append(formatSingleDslForPrompt(entity, dsl));
            sb.append("\n");
        }

        return sb.toString();
    }

    private String formatSingleDslForPrompt(String entity, SemanticQueryWorkflowState.DSL dsl) {
        StringBuilder sb = new StringBuilder();
        sb.append(String.format("Entity: %s\n", entity));

        // Metrics
        if (dsl.getMetrics() != null && !dsl.getMetrics().isEmpty()) {
            sb.append("  Metrics: ").append(String.join(", ", dsl.getMetrics())).append("\n");
        } else {
            sb.append("  Metrics: none\n");
        }

        // Group By
        if (dsl.getGroupBy() != null && !dsl.getGroupBy().isEmpty()) {
            sb.append("  Group By: ").append(String.join(", ", dsl.getGroupBy())).append("\n");
        } else {
            sb.append("  Group By: none\n");
        }

        // Filters
        if (dsl.getFilters() != null && !dsl.getFilters().isEmpty()) {
            sb.append("  Filters: ").append(String.join(", ", dsl.getFilters())).append("\n");
        } else {
            sb.append("  Filters: none\n");
        }

        return sb.toString();
    }

    // ##########################
    // #      초기화 함수들       #
    // ##########################
    private void loadStaticFiles() {
        log.debug("Loading static prompt files");

        try {
            extractFiltersPrompt = fileUtils.loadFile("prompts/extract_filters.system");
            log.debug("Loaded extract_filters.system prompt");

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

                List<Map<String, Object>> metrics = (List<Map<String, Object>>) smYaml.getOrDefault("metrics", new ArrayList<>());
                metricsDict.put(entity, metrics);
                metricsList.addAll(metrics);
                log.debug("Loaded {} metrics for entity '{}'", metrics.size(), entity);

                List<Map<String, Object>> semanticModels = (List<Map<String, Object>>) smYaml.getOrDefault("dbt/models/semantic_models", new ArrayList<>());
                if (!semanticModels.isEmpty()) {
                    Map<String, Object> firstModel = semanticModels.get(0);
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
    }

    private void buildStrings() {
        log.debug("Building dimensions and time dimensions strings");

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
        LocalDate today = LocalDate.now();
        LocalDate yesterday = today.minusDays(1);
        LocalDate thirtyDaysAgo = today.minusDays(30);

        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyyMMdd");
        String todayStr = today.format(formatter);
        String yesterdayStr = yesterday.format(formatter);
        String thirtyDaysAgoStr = thirtyDaysAgo.format(formatter);
        
        return new String[]{todayStr, yesterdayStr, thirtyDaysAgoStr};
    }
}