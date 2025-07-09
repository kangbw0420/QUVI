package com.daquv.agent.workflow.node;

import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.quvi.requests.QueryRequest;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.WebSocketUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Component
public class QueryExecutorNode implements WorkflowNode {
    
    private static final int LIMIT = 100; // 테스트용 LIMIT 값
    
    @Autowired
    @Qualifier("mainJdbcTemplate")
    private JdbcTemplate mainJdbcTemplate;
    
    private final QueryRequest queryRequest;
    
    @Autowired
    private WebSocketUtils webSocketUtils;
    
    public QueryExecutorNode(QueryRequest queryRequest) {
        this.queryRequest = queryRequest;
    }

    @Override
    public String getId() {
        return "executor";
    }

    @Override
    public void execute(WorkflowState state) {
        String sqlQuery = state.getSqlQuery();

        if (sqlQuery == null || sqlQuery.trim().isEmpty()) {
            log.error("SQL 쿼리가 비어있습니다.");
            state.setQueryResultStatus("failed");
            state.setSqlError("SQL 쿼리가 비어있습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("SQL_ERROR", "SQL 쿼리가 비어있습니다."));
            return;
        }

        try {
            log.info("=== QueryExecutorNode 실행 시작 ===");
            log.info("원본 SQL 쿼리: {}", sqlQuery);
            log.info("LIMIT 값: {}", LIMIT);
            
            // 1. 행 수 계산 및 hasNext 설정
            log.info("1단계: 행 수 계산 시작");
            String countResult = queryRequest.countRows(sqlQuery, LIMIT);
            log.info("countRows API 응답: {}", countResult);
            
            int totalRows = 0;
            try {
                totalRows = Integer.parseInt(countResult);
                log.info("파싱된 총 행 수: {}", totalRows);
            } catch (NumberFormatException e) {
                log.warn("행 수 파싱 실패: {}", countResult);
                totalRows = 0;
            }
            
            state.setTotalRows(totalRows);
            log.info("WorkflowState에 설정된 총 행 수: {}", state.getTotalRows());
            
            // hasNext 플래그 설정
            if (totalRows > LIMIT) {
                state.setHasNext(true);
                log.info("✅ 다음 페이지가 존재합니다. 총 행 수: {}, LIMIT: {}", totalRows, LIMIT);
                
                // LIMIT 추가된 쿼리로 실행
                log.info("2단계: LIMIT 추가된 쿼리 생성 시작");
                String limitedQuery = queryRequest.addLimits(sqlQuery, LIMIT, 0);
                log.info("LIMIT 추가된 쿼리: {}", limitedQuery);
                sqlQuery = limitedQuery;
            } else {
                state.setHasNext(false);
                log.info("❌ 다음 페이지가 없습니다. 총 행 수: {}, LIMIT: {}", totalRows, LIMIT);
            }
            
            log.info("최종 hasNext 상태: {}", state.getHasNext());
            
            // 2. 실제 DB 쿼리 실행
            log.info("3단계: 실제 DB 쿼리 실행 시작");
            log.info("실행할 쿼리: {}", sqlQuery);
            
            List<Map<String, Object>> queryResult = mainJdbcTemplate.queryForList(sqlQuery);
            List<String> columnList = extractColumns(sqlQuery, queryResult);

            log.info("쿼리 실행 완료: {} 행 반환", queryResult.size());
            log.info("반환된 컬럼: {}", columnList);

            state.setQueryResult(queryResult);
            state.setColumnList(columnList);
            state.setQueryResultStatus("success");
            
            // WebSocket 메시지 전송 (node.py의 executor 참고)
            Map<String, Object> data = new HashMap<>();
            data.put("result_row", queryResult.size());
            data.put("result_column", columnList.size());
            webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "executor", data);
            
            log.info("=== QueryExecutorNode 실행 완료 ===");
            log.info("최종 상태 - hasNext: {}, totalRows: {}, queryResultSize: {}", 
                    state.getHasNext(), state.getTotalRows(), queryResult.size());

        } catch (Exception e) {
            log.error("❌ QueryExecutorNode 실행 중 예외 발생: {}", e.getMessage(), e);
            state.setQueryResultStatus("failed");
            state.setSqlError("쿼리 실행 실패: " + e.getMessage());
            state.setQueryError(true);
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("QUERY_EXECUTION_ERROR", e.getMessage()));
        }
    }

    /**
     * SQL 쿼리에서 컬럼 이름을 추출합니다.
     * 1차적으로 SQL 파싱을 시도하고, 실패하면 실제 결과에서 키를 가져옵니다.
     */
    private List<String> extractColumns(String sqlQuery, List<Map<String, Object>> queryResult) {
        // 1. SQL에서 컬럼 추출 시도
        List<String> columnsFromSql = extractColumnsFromSql(sqlQuery);
        if (!columnsFromSql.isEmpty()) {
            log.debug("SQL에서 컬럼 추출 성공: {}", columnsFromSql);
            return columnsFromSql;
        }

        // 2. 쿼리 결과에서 컬럼 추출 (fallback)
        List<String> columnsFromResult = extractColumnsFromResult(queryResult);
        log.debug("쿼리 결과에서 컬럼 추출: {}", columnsFromResult);
        return columnsFromResult;
    }

    /**
     * SQL 쿼리 문자열에서 SELECT 절의 컬럼들을 파싱합니다.
     */
    private List<String> extractColumnsFromSql(String sqlQuery) {
        List<String> columns = new ArrayList<>();

        try {
            // SQL을 대소문자 무관하게 정규화
            String normalizedSql = sqlQuery.trim().replaceAll("\\s+", " ");

            // SELECT * 인 경우
            if (normalizedSql.matches("(?i).*SELECT\\s+\\*\\s+FROM.*")) {
                log.debug("SELECT * 쿼리이므로 결과에서 컬럼을 추출합니다.");
                return columns; // 빈 리스트 반환하여 결과에서 추출하도록 함
            }

            // SELECT ... FROM 패턴 매칭
            Pattern selectPattern = Pattern.compile(
                    "(?i)SELECT\\s+(.*?)\\s+FROM",
                    Pattern.CASE_INSENSITIVE | Pattern.DOTALL
            );

            Matcher matcher = selectPattern.matcher(normalizedSql);
            if (matcher.find()) {
                String selectClause = matcher.group(1).trim();

                // 컬럼들을 쉼표로 분리
                String[] columnParts = selectClause.split(",");

                for (String columnPart : columnParts) {
                    String column = cleanColumnName(columnPart.trim());
                    if (!column.isEmpty()) {
                        columns.add(column);
                    }
                }
            }

        } catch (Exception e) {
            log.warn("SQL 파싱 중 오류 발생: {}", e.getMessage());
            return new ArrayList<>(); // 빈 리스트 반환하여 fallback 사용
        }

        return columns;
    }

    /**
     * 컬럼명을 정리합니다 (AS 별칭, 함수 등 처리).
     */
    private String cleanColumnName(String columnPart) {
        // AS 별칭 제거
        if (columnPart.toUpperCase().contains(" AS ")) {
            String[] parts = columnPart.split("(?i)\\s+AS\\s+");
            if (parts.length > 1) {
                columnPart = parts[1].trim();
            }
        }

        // 따옴표 제거
        columnPart = columnPart.replaceAll("[\"']", "");

        // 함수 호출 제거 (예: COUNT(*), SUM(column) 등)
        if (columnPart.contains("(") && columnPart.contains(")")) {
            // 함수명 추출 (예: COUNT, SUM 등)
            String functionName = columnPart.substring(0, columnPart.indexOf("(")).trim();
            if (isReservedWord(functionName)) {
                return functionName.toLowerCase();
            }
        }

        return columnPart.trim();
    }

    /**
     * SQL 예약어인지 확인합니다.
     */
    private boolean isReservedWord(String word) {
        String[] reservedWords = {
                "COUNT", "SUM", "AVG", "MAX", "MIN", "DISTINCT", "CASE", "WHEN", "THEN", "ELSE", "END"
        };
        
        for (String reserved : reservedWords) {
            if (reserved.equalsIgnoreCase(word)) {
                return true;
            }
        }
        return false;
    }

    /**
     * 쿼리 결과에서 컬럼명을 추출합니다.
     */
    private List<String> extractColumnsFromResult(List<Map<String, Object>> queryResult) {
        List<String> columns = new ArrayList<>();
        
        if (queryResult.isEmpty()) {
            return columns;
        }

        // 첫 번째 행의 키를 컬럼명으로 사용
        Map<String, Object> firstRow = queryResult.get(0);
        columns.addAll(firstRow.keySet());

        return columns;
    }
}