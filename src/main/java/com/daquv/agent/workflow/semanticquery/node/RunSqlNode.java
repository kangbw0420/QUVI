package com.daquv.agent.workflow.semanticquery.node;

import com.daquv.agent.quvi.requests.QueryRequest;
import com.daquv.agent.quvi.util.DatabaseProfilerAspect;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.util.WebSocketUtils;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowNode;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState;
import com.daquv.agent.workflow.util.NameModifierUtils;
import com.daquv.agent.workflow.util.PipeTableUtils;
import com.daquv.agent.workflow.util.QueryUtils;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.*;

import static com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState.*;
import static org.hibernate.cfg.AvailableSettings.DIALECT;

@Slf4j
@Component
@RequiredArgsConstructor
public class RunSqlNode implements SemanticQueryWorkflowNode {

    private static final int PAGE_SIZE = 100;

    @Qualifier("mainJdbcTemplate")
    private final JdbcTemplate jdbcTemplate;
    private final WebSocketUtils webSocketUtils;
    private final RequestProfiler requestProfiler;
    private final PipeTableUtils pipeTableUtils;
    private final QueryUtils queryUtils;
    private final NameModifierUtils nameModifierUtils;
    private final QueryRequest queryRequest;

    @Override
    public String getId() {
        return "runSql";
    }

    @Override
    public void execute(SemanticQueryWorkflowState state) {
        String workflowId = state.getWorkflowId();
        
        log.info("Starting SQL execution");

        try {
            Map<String, SemanticQueryExecution> executionMap = 
                state.getSemanticQueryExecutionMap();
            
            if (executionMap == null || executionMap.isEmpty()) {
                log.error("No SemanticQueryExecution found in state. Previous nodes should run first.");
                throw new IllegalStateException("No SemanticQueryExecution found in state");
            }

            int totalExecutionsProcessed = 0;
            int totalQueriesExecuted = 0;

            // 각 SemanticQueryExecution에 대해 처리
            for (Map.Entry<String, SemanticQueryExecution> entry : executionMap.entrySet()) {
                String entity = entry.getKey();
                SemanticQueryExecution execution = entry.getValue();
                
                log.debug("Processing SQL execution for entity: '{}'", entity);

                Map<String, String> sqlMap = execution.getSqlQuery();
                if (sqlMap == null || sqlMap.isEmpty()) {
                    log.warn("No SQL queries found for entity '{}', skipping", entity);
                    continue;
                }

                // SQL 실행 및 결과 저장
                long startTime = System.currentTimeMillis();
                Map<String, Object> resultMap = executeSqlMap(sqlMap, workflowId, state);
                long endTime = System.currentTimeMillis();
                
                double elapsedTime = (endTime - startTime) / 1000.0;
                requestProfiler.recordLlmCall(workflowId, elapsedTime, "run_sql_" + entity);

                // 결과 상태 확인 및 설정
                boolean hasValidResults = false;
                int totalRowsForEntity = 0;

                for (Map.Entry<String, Object> resultEntry : resultMap.entrySet()) {
                    String queryKey = resultEntry.getKey();
                    Object result = resultEntry.getValue();
                    
                    if (result instanceof List) {
                        List<Map<String, Object>> queryResult = (List<Map<String, Object>>) result;
                        
                        // 결과를 execution에 저장
                        execution.addQueryResult(queryKey, queryResult);
                        
                        // 행 수 계산
                        int rows = queryResult.size();
                        execution.addTotalRows(queryKey, rows);
                        totalRowsForEntity += rows;
                        
                        // 빈 결과가 아닌지 확인
                        if (!queryResult.isEmpty() && !isNullOnly(queryResult)) {
                            hasValidResults = true;
                        }
                        
                        log.debug("Executed SQL for entity '{}', query key '{}': {} rows", 
                                 entity, queryKey, rows);
                        totalQueriesExecuted++;
                    }
                }

                // 상태 설정 및 PipeTable 생성
                if (!hasValidResults) {
                    log.warn("No valid data found for entity '{}'", entity);
                    execution.setNoData(true);
                    execution.setTablePipe("(데이터 없음)");
                } else {
                    execution.setQueryResultStatus("success");
                    
                    // 모든 쿼리 결과를 합쳐서 PipeTable 생성
                    List<Map<String, Object>> allResults = new ArrayList<>();
                    for (Object result : resultMap.values()) {
                        if (result instanceof List) {
                            List<Map<String, Object>> queryResult = (List<Map<String, Object>>) result;
                            allResults.addAll(queryResult);
                        }
                    }
                    
                    String tablePipeResult = pipeTableUtils.pipeTable(allResults);
                    execution.setTablePipe(tablePipeResult);
                    log.debug("Generated PipeTable for entity '{}': {} characters", 
                             entity, tablePipeResult.length());
                }

                totalExecutionsProcessed++;
                log.debug("Completed SQL execution for entity '{}'. " +
                         "Executed {} queries, total rows: {}", 
                         entity, sqlMap.size(), totalRowsForEntity);
            }

            // WebSocket 메시지 전송
            Map<String, Object> data = new HashMap<>();
            data.put("processed_executions", totalExecutionsProcessed);
            data.put("total_queries_executed", totalQueriesExecuted);
            data.put("entities_processed", executionMap.keySet());
            webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "run_sql", data);
            
            log.info("SQL execution completed successfully. " +
                    "Processed {} executions, executed {} queries", 
                    totalExecutionsProcessed, totalQueriesExecuted);

        } catch (Exception e) {
            log.error("Failed to execute SQL queries", e);
            throw e;
        }
    }

    private Map<String, Object> executeSqlMap(Map<String, String> sqlMap, String workflowId, SemanticQueryWorkflowState state) {
        Map<String, Object> resultMap = new HashMap<>();

        for (Map.Entry<String, String> entry : sqlMap.entrySet()) {
            String queryKey = entry.getKey();
            String sql = entry.getValue();

            if (sql == null || sql.trim().isEmpty()) {
                log.warn("Empty SQL query for key '{}', skipping", queryKey);
                resultMap.put(queryKey, new ArrayList<>());
                continue;
            }

            try {
//                // Cross-database 참조 문제 해결을 위한 SQL 전처리
//                String processedSql = preprocessSqlForCrossDatabase(sql);
//
//                // 페이지네이션 적용
//                String paginatedSql = countAndPaginate(processedSql, workflowId);

                // 일반 쿼리 처리
                String selectedTable = queryKey;

                // 1. 권한 있는 회사/계좌 검사
                String queryRightCom = queryUtils.addComCondition(sql, state.getUserInfo().getCompanyId());

                // 2. 주식종목/은행명 매핑 변환
                String queryRightStock = nameModifierUtils.modifyStock(queryRightCom);
                String queryRightBank = nameModifierUtils.modifyBank(queryRightStock);

                // 3. order by 추가
                String queryOrdered = queryUtils.addOrderBy(queryRightBank);

                // User Info 추출
                List<String> listOfUserInfo = state.getUserInfo().toArray();

                // parameters에 userInfo 삽입
                List<String> parameters = new ArrayList<>(listOfUserInfo);

                // State에서 필요한 부분 삽입
                parameters.add(state.getStartDate());
                parameters.add(state.getEndDate());

                // 4. view table 적용
                String viewQuery = queryRequest.viewTable(
                        queryOrdered,
                        parameters,
                        DIALECT
                );

                // SQL 실행
                log.debug("Executing SQL for key '{}': {}", queryKey,
                        viewQuery.substring(0, Math.min(100, viewQuery.length())) + "...");

                DatabaseProfilerAspect.setWorkflowId(workflowId);
                List<Map<String, Object>> result = jdbcTemplate.queryForList(viewQuery);

                // 숫자 자동 변환
                List<Map<String, Object>> processedResult = autoCastNumeric(result);

                resultMap.put(queryKey, processedResult);
                log.debug("SQL execution successful for key '{}': {} rows", queryKey, result.size());

            } catch (DataAccessException e) {
                log.error("SQL execution failed for key '{}': {}", queryKey, e.getMessage());

                // Cross-database 오류 특별 처리
                if (isCrossDatabaseError(e)) {
                    log.warn("Cross-database reference detected for key '{}'. Attempting to fix SQL...", queryKey);

                    try {
                        // SQL에서 데이터베이스 참조 제거하고 재시도
                        String fixedSql = fixCrossDatabaseReferences(sql);
                        String paginatedFixedSql = countAndPaginate(fixedSql, workflowId);

                        log.debug("Retrying with fixed SQL for key '{}': {}", queryKey,
                                paginatedFixedSql.substring(0, Math.min(100, paginatedFixedSql.length())) + "...");

                        DatabaseProfilerAspect.setWorkflowId(workflowId);
                        List<Map<String, Object>> result = jdbcTemplate.queryForList(paginatedFixedSql);
                        List<Map<String, Object>> processedResult = autoCastNumeric(result);

                        resultMap.put(queryKey, processedResult);
                        log.info("SQL execution successful after fixing cross-database references for key '{}': {} rows",
                                queryKey, result.size());
                        continue;

                    } catch (Exception retryException) {
                        log.error("Retry after fixing cross-database references also failed for key '{}': {}",
                                queryKey, retryException.getMessage());
                    }
                }

                // 에러 발생 시 에러 정보를 결과에 포함
                Map<String, Object> errorMap = new HashMap<>();
                errorMap.put("error", "SQL execution failed: " + e.getMessage());
                errorMap.put("query_key", queryKey);

                // Cross-database 오류인 경우 더 구체적인 메시지 제공
                if (isCrossDatabaseError(e)) {
                    errorMap.put("error_type", "cross_database_reference");
                    errorMap.put("suggestion", "Check MetricFlow configuration to remove database references from table names");
                }

                resultMap.put(queryKey, Collections.singletonList(errorMap));

            } catch (Exception e) {
                log.error("Unexpected error during SQL execution for key '{}': {}", queryKey, e.getMessage());

                Map<String, Object> errorMap = new HashMap<>();
                errorMap.put("error", "SQL execution failed: " + e.getMessage());
                errorMap.put("query_key", queryKey);
                resultMap.put(queryKey, Collections.singletonList(errorMap));
            }
        }

        return resultMap;
    }

    /**
     * Cross-database 오류인지 확인
     */
    private boolean isCrossDatabaseError(DataAccessException e) {
        String message = e.getMessage();
        return message != null &&
                (message.contains("cross-database references are not implemented") ||
                        message.contains("cross-database"));
    }

    /**
     * SQL 전처리 - Cross-database 참조 제거
     */
    private String preprocessSqlForCrossDatabase(String sql) {
        if (sql == null) {
            return sql;
        }

        // 모든 3단계 참조를 2단계로 변환: "any_db"."schema"."table" -> "schema"."table"
        return sql.replaceAll("\"[^\"]+\"\\.\"([^\"]+)\"\\.\"([^\"]+)\"", "\"$1\".\"$2\"");
    }

    /**
     * Cross-database 참조를 수정하는 범용적인 방법
     */
    private String fixCrossDatabaseReferences(String sql) {
        if (sql == null) {
            return sql;
        }

        String fixedSql = sql;

        // 1. 따옴표로 감싸진 3단계 참조: "database"."schema"."table" -> "schema"."table"
        fixedSql = fixedSql.replaceAll("\"[^\"]+\"\\.\"([^\"]+)\"\\.\"([^\"]+)\"", "\"$1\".\"$2\"");

        // 2. 따옴표 없는 3단계 참조: database.schema.table -> schema.table
        fixedSql = fixedSql.replaceAll("\\b[a-zA-Z_][a-zA-Z0-9_]*\\.([a-zA-Z_][a-zA-Z0-9_]*)\\.([a-zA-Z_][a-zA-Z0-9_]*)", "$1.$2");

        // 3. 혼합형 참조도 처리: database."schema"."table" -> "schema"."table"
        fixedSql = fixedSql.replaceAll("\\b[a-zA-Z_][a-zA-Z0-9_]*\\.\"([^\"]+)\"\\.\"([^\"]+)\"", "\"$1\".\"$2\"");

        // 4. 또 다른 혼합형: "database".schema.table -> schema.table
        fixedSql = fixedSql.replaceAll("\"[^\"]+\"\\.([a-zA-Z_][a-zA-Z0-9_]*)\\.([a-zA-Z_][a-zA-Z0-9_]*)", "$1.$2");

        if (!fixedSql.equals(sql)) {
            log.debug("Fixed cross-database references in SQL:\nBefore: {}\nAfter: {}",
                    sql.substring(0, Math.min(200, sql.length())),
                    fixedSql.substring(0, Math.min(200, fixedSql.length())));
        }

        return fixedSql;
    }

    private String countAndPaginate(String sql, String workflowId) {
        String cleanedSql = sql.trim().replaceAll(";\\s*$", "");
        
        String countSql = String.format(
            "SELECT COUNT(*) AS row_count FROM (%s) AS subq_count", 
            cleanedSql
        );
        
        try {
            DatabaseProfilerAspect.setWorkflowId(workflowId);
            Integer rowCount = jdbcTemplate.queryForObject(countSql, Integer.class);
            
            if (rowCount != null && rowCount > PAGE_SIZE) {
                log.debug("Query has {} rows, applying pagination with limit {}", rowCount, PAGE_SIZE);
                return String.format(
                    "WITH paginated AS (%s) SELECT * FROM paginated LIMIT %d OFFSET 0",
                    cleanedSql, PAGE_SIZE
                );
            } else {
                log.debug("Query has {} rows, no pagination needed", rowCount);
            }
        } catch (DataAccessException e) {
            log.warn("Failed to count rows for pagination: {}", e.getMessage());
        }
        
        return sql;
    }

    private List<Map<String, Object>> autoCastNumeric(List<Map<String, Object>> data) {
        if (data == null || data.isEmpty()) {
            return data;
        }
        
        List<Map<String, Object>> result = new ArrayList<>();
        
        for (Map<String, Object> row : data) {
            Map<String, Object> processedRow = new HashMap<>();
            
            for (Map.Entry<String, Object> entry : row.entrySet()) {
                String key = entry.getKey();
                Object value = entry.getValue();
                
                if (value instanceof String) {
                    String strValue = (String) value;
                    Object convertedValue = tryParseNumeric(strValue);
                    processedRow.put(key, convertedValue);
                } else {
                    processedRow.put(key, value);
                }
            }
            
            result.add(processedRow);
        }
        
        return result;
    }

    private Object tryParseNumeric(String value) {
        if (value == null || value.trim().isEmpty()) {
            return value;
        }
        
        String trimmed = value.trim();
        
        try {
            if (trimmed.contains(".")) {
                return new BigDecimal(trimmed);
            } else {
                return Long.parseLong(trimmed);
            }
        } catch (NumberFormatException e) {
            return value;
        }
    }

    /**
     * 쿼리 결과가 모두 null인지 확인합니다.
     * SemanticQueryExecutorNode의 queryUtils.isNullOnly() 기능을 복제
     */
    private boolean isNullOnly(List<Map<String, Object>> queryResult) {
        if (queryResult == null || queryResult.isEmpty()) {
            return true;
        }
        
        for (Map<String, Object> row : queryResult) {
            for (Object value : row.values()) {
                if (value != null) {
                    return false;
                }
            }
        }
        
        return true;
    }
}