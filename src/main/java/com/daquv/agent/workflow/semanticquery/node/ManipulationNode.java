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
import java.util.*;

import static com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState.*;

@Slf4j
@Component
@RequiredArgsConstructor
public class ManipulationNode implements SemanticQueryWorkflowNode {

    private final LLMRequest llmRequest;
    private final ResponseParser responseParser;
    private final FileUtils fileUtils;
    private final YamlUtils yamlUtils;
    private final WebSocketUtils webSocketUtils;
    private final RequestProfiler requestProfiler;

    private static final String[] ENTITIES = SemanticEntity.getValues();

    private String extractOrderByAndLimitPrompt;
    private Map<String, List<Map<String, Object>>> metricsDict = new HashMap<>();

    // 필수 group_by 설정
    private static final Map<String, Set<String>> REQUIRED_GROUP_BYS;
    static {
        REQUIRED_GROUP_BYS = new HashMap<>();
        
        Set<String> balRequiredGroupBys = new HashSet<>();
        balRequiredGroupBys.add("acct__view_dv");
        balRequiredGroupBys.add("acct__curr_cd");
        REQUIRED_GROUP_BYS.put("bal", balRequiredGroupBys);
        
        Set<String> balForeRequiredGroupBys = new HashSet<>();
        balForeRequiredGroupBys.add("acct__view_dv");
        balForeRequiredGroupBys.add("acct__curr_cd");
        REQUIRED_GROUP_BYS.put("bal_fore", balForeRequiredGroupBys);
        
        Set<String> trscRequiredGroupBys = new HashSet<>();
        trscRequiredGroupBys.add("acct__curr_cd");
        REQUIRED_GROUP_BYS.put("trsc", trscRequiredGroupBys);
        
        Set<String> trscForeRequiredGroupBys = new HashSet<>();
        trscForeRequiredGroupBys.add("acct__curr_cd");
        REQUIRED_GROUP_BYS.put("trsc_fore", trscForeRequiredGroupBys);
    }

    @PostConstruct
    public void init() {
        log.info("Initializing ManipulationNode...");

        try {
            loadStaticFiles();
            log.info("Static files loaded successfully");

            loadSemanticModels();
            log.info("Semantic models loaded successfully");

            log.info("ManipulationNode initialization completed successfully");
        } catch (Exception e) {
            log.error("Failed to initialize ManipulationNode", e);
            throw e;
        }
    }

    @Override
    public String getId() {
        return "manipulation";
    }

    @Override
    public void execute(SemanticQueryWorkflowState state) {
        String userQuestion = state.getUserQuestion();
        String workflowId = state.getWorkflowId();
        
        log.info("Starting order by, limit extraction and custom manipulation for user question: '{}'", userQuestion);

        try {
            Map<String, SemanticQueryExecution> executionMap =
                state.getSemanticQueryExecutionMap();
            
            if (executionMap == null || executionMap.isEmpty()) {
                log.error("No SemanticQueryExecution found in state. Previous nodes should run first.");
                throw new IllegalStateException("No SemanticQueryExecution found in state");
            }

            int totalExecutionsProcessed = 0;

            // 각 SemanticQueryExecution에 대해 처리
            for (Map.Entry<String, SemanticQueryExecution> entry : executionMap.entrySet()) {
                String entity = entry.getKey();
                SemanticQueryExecution execution = entry.getValue();
                
                log.debug("Processing SemanticQueryExecution for entity: '{}'", entity);

                // 1. order_by와 limit 추출
                long startTime = System.currentTimeMillis();
                Map<String, DSL> updatedDsls =
                    extractOrderByAndLimit(userQuestion, execution.getDsl());
                long endTime = System.currentTimeMillis();
                
                double elapsedTime = (endTime - startTime) / 1000.0;
                requestProfiler.recordLlmCall(workflowId, elapsedTime, "manipulation_orderby_" + entity);

                // 2. 커스텀 조작 적용 (날짜 정보 생성)
                String todayStr = createTodayString();
                log.debug("Today string: {}", todayStr);
                Map<String, DSL> finalDsls = customManipulation(updatedDsls, todayStr);

                // 3. execution의 DSL 업데이트
                execution.setDsl(finalDsls);
                totalExecutionsProcessed++;

                log.debug("Completed processing for entity '{}'. DSL entities: {}", 
                         entity, finalDsls.keySet());
            }

            // WebSocket 메시지 전송
            Map<String, Object> data = new HashMap<>();
            data.put("processed_executions", totalExecutionsProcessed);
            data.put("entities_processed", executionMap.keySet());
            webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "manipulation", data);
            
            log.info("Order by, limit extraction and custom manipulation completed successfully. " +
                    "Processed {} executions", totalExecutionsProcessed);

        } catch (Exception e) {
            log.error("Failed to process manipulations for question: '{}'", userQuestion, e);
            throw e;
        }
    }

    private Map<String, DSL> extractOrderByAndLimit(
            String userInput, Map<String, DSL> dsls) {
        
        log.debug("Extracting order by and limit for {} entities", dsls.size());
        Map<String, DSL> finalDsls = new HashMap<>();

        for (Map.Entry<String, DSL> entry : dsls.entrySet()) {
            String entity = entry.getKey();
            DSL dsl = entry.getValue();

            log.debug("Processing order by and limit for entity '{}'", entity);
            String singleDslString = formatSingleDslForPrompt(entity, dsl);
            log.debug("Single DSL string for entity '{}': {}", entity, singleDslString);

            String formattedPrompt = extractOrderByAndLimitPrompt.replace("{dsl}", singleDslString);
            String response = llmRequest.callQwenLlm(formattedPrompt, userInput);

            Map<String, Object> parsedResponse = responseParser.parseResponse(response);

            if (parsedResponse.containsKey(entity)) {
                Map<String, Object> entityData = (Map<String, Object>) parsedResponse.get(entity);
                List<String> orderBy = (List<String>) entityData.getOrDefault("order_by", new ArrayList<>());
                Integer limit = (Integer) entityData.get("limit");

                dsl.setOrderBy(orderBy);
                dsl.setLimit(limit);
                log.debug("Set order by ({} items) and limit ({}) for entity '{}'",
                        orderBy.size(), limit, entity);
            } else {
                List<String> orderBy = (List<String>) parsedResponse.getOrDefault("order_by", new ArrayList<>());
                Integer limit = (Integer) parsedResponse.get("limit");

                dsl.setOrderBy(orderBy);
                dsl.setLimit(limit);
                log.debug("Set default order by ({} items) and limit ({}) for entity '{}'",
                        orderBy.size(), limit, entity);
            }

            finalDsls.put(entity, dsl);
        }

        log.info("Order by and limit extraction completed for {} entities", finalDsls.size());
        return finalDsls;
    }

    private Map<String, DSL> customManipulation(
            Map<String, DSL> dsls, String todayStr) {
        
        log.debug("Applying custom manipulations to {} DSLs", dsls.size());

        // 1. bal과 bal_fore에 reg_dt 필터 추가
        addDefaultDateFilters(dsls, todayStr);

        // 2. 필수 group_by 추가
        addRequiredGroupBys(dsls);

        // 3. ORDER BY 컬럼을 metrics/group_by에 추가
        addOrderByColumns(dsls);

        log.info("Custom manipulations completed");
        return dsls;
    }

    private void addDefaultDateFilters(Map<String, DSL> dsls, String todayStr) {
        log.debug("Adding default date filters");

        if (dsls.containsKey("bal")) {
            DSL balDsl = dsls.get("bal");
            boolean hasRegDtFilter = false;
            for (String f : balDsl.getFilters()) {
                if (f.contains("bal__reg_dt")) {
                    hasRegDtFilter = true;
                    break;
                }
            }
            if (!hasRegDtFilter) {
                String filter = String.format("{{ TimeDimension('bal__reg_dt') }} IN ('%s')", todayStr);
                balDsl.getFilters().add(filter);
                log.debug("Added default reg_dt filter to 'bal' entity: '{}'", filter);
            } else {
                log.debug("'bal' entity already has reg_dt filter, skipping default");
            }
        }

        if (dsls.containsKey("bal_fore")) {
            DSL balForeDsl = dsls.get("bal_fore");
            boolean hasRegDtFilter = false;
            for (String f : balForeDsl.getFilters()) {
                if (f.contains("bal_fore__reg_dt")) {
                    hasRegDtFilter = true;
                    break;
                }
            }
            if (!hasRegDtFilter) {
                String filter = String.format("{{ TimeDimension('bal_fore__reg_dt') }} IN ('%s')", todayStr);
                balForeDsl.getFilters().add(filter);
                log.debug("Added default reg_dt filter to 'bal_fore' entity: '{}'", filter);
            } else {
                log.debug("'bal_fore' entity already has reg_dt filter, skipping default");
            }
        }
    }

    private void addRequiredGroupBys(Map<String, DSL> dsls) {
        log.debug("Adding required group by items");

        for (Map.Entry<String, DSL> entry : dsls.entrySet()) {
            String entity = entry.getKey();
            DSL dsl = entry.getValue();

            Set<String> requiredGroupBys = REQUIRED_GROUP_BYS.getOrDefault(entity, new HashSet<>());
            int addedCount = 0;

            for (String groupBy : requiredGroupBys) {
                if (!dsl.getGroupBy().contains(groupBy)) {
                    dsl.getGroupBy().add(groupBy);
                    addedCount++;
                }
            }

            if (addedCount > 0) {
                log.debug("Added {} required group by items to entity '{}': {}",
                        addedCount, entity, requiredGroupBys);
            }
        }
    }

    private void addOrderByColumns(Map<String, DSL> dsls) {
        log.debug("Adding order by columns to metrics/group_by");

        for (Map.Entry<String, DSL> entry : dsls.entrySet()) {
            String entity = entry.getKey();
            DSL dsl = entry.getValue();

            List<String> orderByCols = new ArrayList<>();
            for (String col : dsl.getOrderBy()) {
                if (col.startsWith("-")) {
                    orderByCols.add(col.substring(1));
                } else {
                    orderByCols.add(col);
                }
            }

            int metricsAdded = 0;
            int groupByAdded = 0;

            for (String col : orderByCols) {
                boolean isMetric = isMetricColumn(entity, col);
                if (isMetric) {
                    if (!dsl.getMetrics().contains(col)) {
                        dsl.getMetrics().add(col);
                        metricsAdded++;
                    }
                } else {
                    if (!dsl.getGroupBy().contains(col)) {
                        dsl.getGroupBy().add(col);
                        groupByAdded++;
                    }
                }
            }

            if (metricsAdded > 0 || groupByAdded > 0) {
                log.debug("Added order by columns to entity '{}': {} metrics, {} group by items",
                        entity, metricsAdded, groupByAdded);
            }
        }
    }

    private boolean isMetricColumn(String entity, String column) {
        List<Map<String, Object>> entityMetrics = metricsDict.get(entity);
        if (entityMetrics == null) {
            entityMetrics = new ArrayList<>();
        }
        boolean isMetric = false;
        for (Map<String, Object> metric : entityMetrics) {
            if (column.equals(metric.get("name"))) {
                isMetric = true;
                break;
            }
        }

        log.trace("Column '{}' in entity '{}' is metric: {}", column, entity, isMetric);
        return isMetric;
    }

    private String formatSingleDslForPrompt(String entity, DSL dsl) {
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

        // Order By
        if (dsl.getOrderBy() != null && !dsl.getOrderBy().isEmpty()) {
            sb.append("  Order By: ").append(String.join(", ", dsl.getOrderBy())).append("\n");
        } else {
            sb.append("  Order By: none\n");
        }

        // Limit
        if (dsl.getLimit() != null) {
            sb.append("  Limit: ").append(dsl.getLimit()).append("\n");
        } else {
            sb.append("  Limit: none\n");
        }

        return sb.toString();
    }

    // ##########################
    // #      초기화 함수들       #
    // ##########################
    private void loadStaticFiles() {
        log.debug("Loading static prompt files");

        try {
            extractOrderByAndLimitPrompt = fileUtils.loadFile("prompts/extract_order_by_and_limit.system");
            log.debug("Loaded extract_order_by_and_limit.system prompt");

        } catch (Exception e) {
            log.error("Failed to load static files", e);
            throw e;
        }
    }

    private void loadSemanticModels() {
        log.debug("Loading semantic models for metrics dictionary");

        for (String entity : ENTITIES) {
            try {
                log.debug("Loading semantic model for entity: '{}'", entity);
                Map<String, Object> smYaml = yamlUtils.loadYaml(String.format("dbt/models/semantic_models/%s.yml", entity));

                List<Map<String, Object>> metrics = (List<Map<String, Object>>) smYaml.getOrDefault("metrics", new ArrayList<>());
                metricsDict.put(entity, metrics);
                log.debug("Loaded {} metrics for entity '{}'", metrics.size(), entity);

            } catch (Exception e) {
                log.error("Failed to load semantic model for entity '{}'", entity, e);
                throw e;
            }
        }
    }

    private String createTodayString() {
        LocalDate today = LocalDate.now();
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyyMMdd");
        return today.format(formatter);
    }
}