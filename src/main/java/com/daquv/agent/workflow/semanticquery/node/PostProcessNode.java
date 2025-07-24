package com.daquv.agent.workflow.semanticquery.node;

import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.util.WebSocketUtils;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowNode;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState;
import com.daquv.agent.workflow.semanticquery.utils.FileUtils;
import com.daquv.agent.workflow.semanticquery.utils.SQLCleanUtils;
import com.daquv.agent.workflow.util.LLMRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.sql.*;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;

import static com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState.*;

@Slf4j
@Component
@RequiredArgsConstructor
public class PostProcessNode implements SemanticQueryWorkflowNode {

    private final LLMRequest llmRequest;
    private final FileUtils fileUtils;
    private final SQLCleanUtils sqlCleanUtils;
    private final WebSocketUtils webSocketUtils;
    private final RequestProfiler requestProfiler;

    @Override
    public String getId() {
        return "postProcess";
    }

    @Override
    public void execute(SemanticQueryWorkflowState state) {
        String userQuestion = state.getUserQuestion();
        String workflowId = state.getWorkflowId();
        
        log.info("Starting DuckDB post-processing for user question: '{}'", userQuestion);

        try {
            Map<String, SemanticQueryExecution> executionMap = 
                state.getSemanticQueryExecutionMap();
            
            if (executionMap == null || executionMap.isEmpty()) {
                log.error("No SemanticQueryExecution found in state. Previous nodes should run first.");
                throw new IllegalStateException("No SemanticQueryExecution found in state");
            }

            int totalExecutionsProcessed = 0;
            int totalPostProcessed = 0;

            // 각 SemanticQueryExecution에 대해 처리
            for (Map.Entry<String, SemanticQueryExecution> entry : executionMap.entrySet()) {
                String entity = entry.getKey();
                SemanticQueryExecution execution = entry.getValue();
                
                log.debug("Processing DuckDB post-processing for entity: '{}'", entity);

                // DSL과 쿼리 결과가 있는지 확인
                Map<String, DSL> dslMap = execution.getDsl();
                Map<String, Object> queryResultMap = execution.getQueryResult();
                
                if (dslMap == null || dslMap.isEmpty()) {
                    log.warn("No DSL found for entity '{}', skipping post-processing", entity);
                    continue;
                }
                
                if (queryResultMap == null || queryResultMap.isEmpty()) {
                    log.warn("No query results found for entity '{}', skipping post-processing", entity);
                    continue;
                }

                // DuckDB 후처리 실행
                long startTime = System.currentTimeMillis();
                List<Map<String, Object>> postProcessedResult = 
                    postProcessWithDuckDB(userQuestion, dslMap, queryResultMap);
                long endTime = System.currentTimeMillis();
                
                double elapsedTime = (endTime - startTime) / 1000.0;
                requestProfiler.recordLlmCall(workflowId, elapsedTime, "post_process_" + entity);

                // 후처리 결과를 execution에 저장
                execution.setPostQueryResult(postProcessedResult);
                
                if (postProcessedResult != null && !postProcessedResult.isEmpty()) {
                    totalPostProcessed++;
                    log.debug("Post-processing completed for entity '{}': {} rows", 
                             entity, postProcessedResult.size());
                } else {
                    log.warn("Post-processing returned empty result for entity '{}'", entity);
                }

                totalExecutionsProcessed++;
            }

            // WebSocket 메시지 전송
            Map<String, Object> data = new HashMap<>();
            data.put("processed_executions", totalExecutionsProcessed);
            data.put("total_post_processed", totalPostProcessed);
            data.put("entities_processed", executionMap.keySet());
            webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "post_process", data);
            
            log.info("DuckDB post-processing completed successfully. " +
                    "Processed {} executions, {} with results", 
                    totalExecutionsProcessed, totalPostProcessed);

        } catch (Exception e) {
            log.error("Failed to execute DuckDB post-processing for question: '{}'", userQuestion, e);
            throw e;
        }
    }

    private List<Map<String, Object>> postProcessWithDuckDB(
            String userInput, 
            Map<String, DSL> dslMap, 
            Map<String, Object> queryResultMap) {
        
        // 날짜 정보 생성 (매번 최신 날짜 사용)
        String today = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyyMMdd"));
        
        // 프롬프트 생성
        String systemPrompt = fileUtils.loadFile("prompts/duckdb_postprocess.system");
        String formattedPrompt = systemPrompt
                .replace("{today}", today)
                .replace("{user_input}", userInput)
                .replace("{dsl}", formatDslMapForPrompt(dslMap))
                .replace("{result_df}", formatQueryResultMapForPrompt(queryResultMap));
        
        log.debug("Calling LLM for DuckDB post-processing");
        String rawSql = llmRequest.callQwenLlm(formattedPrompt, userInput);
        log.debug("LLM response received, length: {} characters", rawSql.length());
        
        // SQL 정리
        String cleanedSql = sqlCleanUtils.fixMismatchedQuotes(
            rawSql.replace("sql", "").replace("`", "").trim()
        );
        log.debug("Cleaned SQL: {}", cleanedSql);

        return executeDuckDBQuery(cleanedSql, queryResultMap);
    }
    
    private List<Map<String, Object>> executeDuckDBQuery(String sql, Map<String, Object> queryResultMap) {
        List<Map<String, Object>> result = new ArrayList<>();
        Connection conn = null;
        Statement stmt = null;
        ResultSet rs = null;
        
        try {
            log.debug("Connecting to DuckDB and executing query");
            conn = DriverManager.getConnection("jdbc:duckdb:");
            
            // 테이블 등록
            registerTables(conn, queryResultMap);
            
            // SQL 실행
            stmt = conn.createStatement();
            rs = stmt.executeQuery(sql);
            
            // 결과 처리
            ResultSetMetaData metaData = rs.getMetaData();
            int columnCount = metaData.getColumnCount();
            
            while (rs.next()) {
                Map<String, Object> row = new HashMap<>();
                for (int i = 1; i <= columnCount; i++) {
                    String columnName = metaData.getColumnName(i);
                    Object value = rs.getObject(i);
                    row.put(columnName, value);
                }
                result.add(row);
            }
            
            log.debug("DuckDB query executed successfully: {} rows returned", result.size());
            
        } catch (Exception e) {
            log.error("DuckDB execution failed: {}", e.getMessage(), e);
            Map<String, Object> errorMap = new HashMap<>();
            errorMap.put("error", "DuckDB execution failed: " + e.getMessage());
            result.add(errorMap);
        } finally {
            try {
                if (rs != null) rs.close();
                if (stmt != null) stmt.close();
                if (conn != null) conn.close();
            } catch (SQLException e) {
                log.warn("Error closing DuckDB resources: {}", e.getMessage());
            }
        }
        
        return result;
    }
    
    private void registerTables(Connection conn, Map<String, Object> queryResultMap) throws SQLException {
        for (Map.Entry<String, Object> entry : queryResultMap.entrySet()) {
            String tableName = entry.getKey();
            Object data = entry.getValue();
            
            if (data instanceof List) {
                List<Map<String, Object>> tableData = (List<Map<String, Object>>) data;
                registerDataFrameTable(conn, tableName, tableData);
                log.debug("Registered table '{}' with {} rows", tableName, tableData.size());
            }
        }
    }
    
    private void registerDataFrameTable(Connection conn, String tableName, List<Map<String, Object>> data) throws SQLException {
        if (data == null || data.isEmpty()) {
            log.debug("Skipping empty table '{}'", tableName);
            return;
        }
        
        Map<String, Object> firstRow = data.get(0);
        if (firstRow.isEmpty()) {
            log.debug("Skipping table '{}' with empty first row", tableName);
            return;
        }
        
        List<String> columnNames = new ArrayList<>(firstRow.keySet());
        
        // Create table with proper column definitions
        StringBuilder createTableSql = new StringBuilder("CREATE OR REPLACE TABLE ");
        createTableSql.append(tableName).append(" (");
        
        // Determine column types from first row
        boolean firstCol = true;
        for (String columnName : columnNames) {
            if (!firstCol) {
                createTableSql.append(", ");
            }
            createTableSql.append(columnName);
            
            Object value = firstRow.get(columnName);
            if (value instanceof Number) {
                createTableSql.append(" DOUBLE");
            } else {
                createTableSql.append(" VARCHAR");
            }
            firstCol = false;
        }
        createTableSql.append(")");
        
        Statement stmt = conn.createStatement();
        stmt.execute(createTableSql.toString());
        
        // Insert data
        StringBuilder insertSql = new StringBuilder("INSERT INTO ");
        insertSql.append(tableName).append(" VALUES ");
        
        for (int i = 0; i < data.size(); i++) {
            Map<String, Object> row = data.get(i);
            if (i > 0) {
                insertSql.append(", ");
            }
            insertSql.append("(");
            
            boolean firstValue = true;
            for (String columnName : columnNames) {
                if (!firstValue) {
                    insertSql.append(", ");
                }
                Object value = row.get(columnName);
                if (value == null) {
                    insertSql.append("NULL");
                } else if (value instanceof Number) {
                    insertSql.append(value.toString());
                } else {
                    insertSql.append("'").append(value.toString().replace("'", "''")).append("'");
                }
                firstValue = false;
            }
            insertSql.append(")");
        }
        
        stmt.execute(insertSql.toString());
        stmt.close();
    }

    // ##########################
    // #    포맷팅 유틸리티       #
    // ##########################

    /**
     * DSL Map을 프롬프트에 사용할 수 있는 읽기 쉬운 형태로 변환
     */
    private String formatDslMapForPrompt(Map<String, DSL> dslMap) {
        if (dslMap == null || dslMap.isEmpty()) {
            return "No DSL found.";
        }

        StringBuilder sb = new StringBuilder();
        sb.append("DSL Configuration:\n");

        for (Map.Entry<String, DSL> entry : dslMap.entrySet()) {
            String entity = entry.getKey();
            DSL dsl = entry.getValue();
            sb.append(formatSingleDslForPrompt(entity, dsl));
            sb.append("\n");
        }

        return sb.toString();
    }

    /**
     * 쿼리 결과 Map을 프롬프트용 문자열로 변환
     */
    private String formatQueryResultMapForPrompt(Map<String, Object> queryResultMap) {
        if (queryResultMap == null || queryResultMap.isEmpty()) {
            return "No query results found.";
        }

        StringBuilder sb = new StringBuilder();
        sb.append("Query Results:\n");

        for (Map.Entry<String, Object> entry : queryResultMap.entrySet()) {
            String key = entry.getKey();
            Object value = entry.getValue();
            
            if (value instanceof List) {
                sb.append(String.format("  %s: %s\n", key, formatListForPrompt((List<?>) value)));
            } else {
                sb.append(String.format("  %s: %s\n", key, value != null ? value.toString() : "null"));
            }
        }

        return sb.toString();
    }

    /**
     * List를 프롬프트용 문자열로 변환
     */
    private String formatListForPrompt(List<?> list) {
        if (list == null || list.isEmpty()) {
            return "[]";
        }
        
        if (list.size() <= 3) {
            return list.toString();
        }
        
        return String.format("[%s, %s, %s, ... (%d more items)]", 
                list.get(0), list.get(1), list.get(2), list.size() - 3);
    }

    /**
     * 단일 DSL 객체를 프롬프트용 문자열로 변환
     */
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
}