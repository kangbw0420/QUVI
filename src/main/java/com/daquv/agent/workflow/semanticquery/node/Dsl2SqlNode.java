package com.daquv.agent.workflow.semanticquery.node;

import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.util.WebSocketUtils;
import com.daquv.agent.requests.MetricFlowRequest;
import com.daquv.agent.workflow.dto.MetricFlowRequestDto;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowNode;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState;
import com.daquv.agent.workflow.semanticquery.utils.SQLCleanUtils;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

import static com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState.DSL;
import static com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState.SemanticQueryExecution;

@Slf4j
@Component
@RequiredArgsConstructor
public class Dsl2SqlNode implements SemanticQueryWorkflowNode {

    private final MetricFlowRequest metricFlowRequest;
    private final SQLCleanUtils sqlCleanUtils;
    private final WebSocketUtils webSocketUtils;
    private final RequestProfiler requestProfiler;

    @Override
    public String getId() {
        return "dsl2sql";
    }

    @Override
    public void execute(SemanticQueryWorkflowState state) {
        String workflowId = state.getWorkflowId();
        
        log.info("Starting DSL to SQL conversion");

        try {
            Map<String, SemanticQueryExecution> executionMap = 
                state.getSemanticQueryExecutionMap();
            
            if (executionMap == null || executionMap.isEmpty()) {
                log.error("No SemanticQueryExecution found in state. Previous nodes should run first.");
                throw new IllegalStateException("No SemanticQueryExecution found in state");
            }

            int totalExecutionsProcessed = 0;
            int totalSqlGenerated = 0;

            // 각 SemanticQueryExecution에 대해 처리
            for (Map.Entry<String, SemanticQueryExecution> entry : executionMap.entrySet()) {
                String entity = entry.getKey();
                SemanticQueryExecution execution = entry.getValue();
                
                log.debug("Processing DSL to SQL conversion for entity: '{}'", entity);

                Map<String, DSL> dslMap = execution.getDsl();
                if (dslMap == null || dslMap.isEmpty()) {
                    log.warn("No DSL found for entity '{}', skipping", entity);
                    continue;
                }

                // DSL을 SQL로 변환
                long startTime = System.currentTimeMillis();
                Map<String, String> sqlMap = convertDslToSql(dslMap);
                long endTime = System.currentTimeMillis();
                
                double elapsedTime = (endTime - startTime) / 1000.0;
                requestProfiler.recordLlmCall(workflowId, elapsedTime, "dsl2sql_" + entity);

                // SQL 쿼리를 execution에 저장
                for (Map.Entry<String, String> sqlEntry : sqlMap.entrySet()) {
                    String queryKey = sqlEntry.getKey();
                    String sql = sqlEntry.getValue();
                    execution.addSqlQuery(queryKey, sql);
                    totalSqlGenerated++;
                    log.debug("Generated SQL for entity '{}', query key '{}': {}", 
                             entity, queryKey, sql.substring(0, Math.min(100, sql.length())) + "...");
                }

                totalExecutionsProcessed++;
                log.debug("Completed DSL to SQL conversion for entity '{}'. Generated {} SQL queries", 
                         entity, sqlMap.size());
            }

            // WebSocket 메시지 전송
            Map<String, Object> data = new HashMap<>();
            data.put("processed_executions", totalExecutionsProcessed);
            data.put("total_sql_generated", totalSqlGenerated);
            data.put("entities_processed", executionMap.keySet());
            webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "dsl2sql", data);
            
            log.info("DSL to SQL conversion completed successfully. " +
                    "Processed {} executions, generated {} SQL queries", 
                    totalExecutionsProcessed, totalSqlGenerated);

        } catch (Exception e) {
            log.error("Failed to convert DSL to SQL", e);
            throw e;
        }
    }

    private Map<String, String> convertDslToSql(Map<String, DSL> dslMap) {
        Map<String, String> sqlMap = new HashMap<>();

        try {
            // 1. DSL을 MetricFlow 요청 형태로 변환
            Map<String, MetricFlowRequestDto> metricFlowRequests = convertDslToMetricFlowRequests(dslMap);
            log.debug("Converted {} DSL entries to MetricFlow requests", metricFlowRequests.size());

            // 2. Python 서버에 일괄 요청
            Map<String, String> rawSqlResults = metricFlowRequest.generateSqlFromDsl(metricFlowRequests);
            log.debug("Received {} raw SQL results from MetricFlow", rawSqlResults.size());

            // 3. Java에서 SQL 후처리
            for (Map.Entry<String, String> entry : rawSqlResults.entrySet()) {
                String queryKey = entry.getKey();
                String rawSql = entry.getValue();

                log.debug("Processing raw SQL for query key '{}': {}", 
                         queryKey, rawSql.substring(0, Math.min(200, rawSql.length())) + "...");

                // SQL 정리 및 수정
                String cleanSql = sqlCleanUtils.extractCleanSql(rawSql);
                log.trace("Cleaned SQL: {}", cleanSql);

                // 날짜 형식 수정
                cleanSql = cleanSql.replace(
                        "TO_DATE(CAST(trsc_dt AS TEXT), 'YYYY-MM-DD')",
                        "TO_DATE(CAST(trsc_dt AS TEXT), 'YYYYMMDD')"
                );

                String modifiedSql = sqlCleanUtils.modifyQuery(cleanSql);
                log.trace("Modified SQL: {}", modifiedSql);

                sqlMap.put(queryKey, modifiedSql);
            }

            log.info("Successfully converted {} DSL entries to SQL", sqlMap.size());

        } catch (Exception e) {
            log.error("DSL to SQL conversion failed", e);
            // 에러 발생 시 에러 메시지를 SQL 맵에 저장
            sqlMap.put("error", "DSL to SQL conversion failed: " + e.getMessage());
        }

        return sqlMap;
    }

    private Map<String, MetricFlowRequestDto> convertDslToMetricFlowRequests(Map<String, DSL> dslMap) {
        Map<String, MetricFlowRequestDto> requests = new HashMap<>();

        for (Map.Entry<String, DSL> entry : dslMap.entrySet()) {
            String queryKey = entry.getKey();
            DSL dslQuery = entry.getValue();

            MetricFlowRequestDto request = MetricFlowRequestDto.builder()
                    .metrics(dslQuery.getMetrics())
                    .groupBy(dslQuery.getGroupBy())
                    .filters(dslQuery.getFilters())
                    .orderBy(dslQuery.getOrderBy())
                    .limit(normalizeLimit(dslQuery.getLimit()))
                    .build();

            requests.put(queryKey, request);
            log.debug("Created MetricFlow request for query key '{}': metrics={}, groupBy={}, filters={}, orderBy={}, limit={}", 
                     queryKey, request.getMetrics().size(), request.getGroupBy().size(), 
                     request.getFilters().size(), request.getOrderBy().size(), request.getLimit());
        }

        return requests;
    }

    private Integer normalizeLimit(Object limit) {
        if (limit == null || "".equals(limit)) {
            return null;
        }

        if (limit instanceof String) {
            String limitStr = (String) limit;
            if (limitStr.trim().isEmpty()) {
                return null;
            }
            try {
                return Integer.parseInt(limitStr);
            } catch (NumberFormatException e) {
                log.warn("Failed to parse limit string '{}': {}", limitStr, e.getMessage());
                return null;
            }
        }

        if (limit instanceof Integer) {
            return (Integer) limit;
        }

        log.warn("Unsupported limit type: {}", limit.getClass().getSimpleName());
        return null;
    }
}