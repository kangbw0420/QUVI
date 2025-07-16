package com.daquv.agent.workflow.node;

import com.daquv.agent.quvi.util.LlmOutputHandler;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.quvi.llmadmin.QnaService;
import com.daquv.agent.quvi.requests.QueryRequest;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import com.daquv.agent.workflow.util.LLMRequest;
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
public class SafeguardNode implements WorkflowNode {

    private static final int LIMIT = 100;

    @Autowired
    private LLMRequest llmService;

    @Autowired
    private PromptBuilder promptBuilder;
    
    @Autowired
    private QnaService qnaService;
    
    @Autowired
    @Qualifier("mainJdbcTemplate")
    private JdbcTemplate mainJdbcTemplate;
    
    private final QueryRequest queryRequest;
    
    @Autowired
    private WebSocketUtils webSocketUtils;

    @Autowired
    private RequestProfiler requestProfiler;
    
    public SafeguardNode(QueryRequest queryRequest) {
        this.queryRequest = queryRequest;
    }

    @Override
    public String getId() {
        return "safeguard";
    }

    @Override
    public void execute(WorkflowState state) {
        state.incrementSafeCount();
        String unsafeQuery = state.getSqlQuery();
        String userQuestion = state.getUserQuestion();
        String sqlError = state.getSqlError();
        Boolean queryError = state.getQueryError();
        String chainId = state.getChainId();

        if (unsafeQuery == null || unsafeQuery.trim().isEmpty()) {
            log.error("수정할 SQL 쿼리가 비어있습니다.");
            return;
        }

        try {
            log.info("1단계: 에러에 따른 프롬프트 분기");
            PromptTemplate promptTemplate = null;
            // 1. 쿼리 에러 확인
            if (queryError) {
                promptTemplate = promptBuilder.buildSafeguardPrompt(userQuestion, unsafeQuery, sqlError);
            } else {
                String questionWithError = String.format("%s, SQL오류: %s", userQuestion, sqlError);
                promptTemplate = promptBuilder.buildNL2SQLPrompt(questionWithError);
            }
            String prompt = promptTemplate.build();

            log.info("2단계: QnA ID 생성");
            String qnaId = qnaService.createQnaId(state.getTraceId());
            log.info("생성된 QnA ID: {}", qnaId);

            log.info("3단계: LLM을 통한 쿼리 수정 시작");
            String modifiedQuery = llmService.callNl2sql(prompt, qnaId);
            modifiedQuery = LlmOutputHandler.handleSqlCodeBlock(modifiedQuery);
            log.info("수정된 쿼리: {}", modifiedQuery);
            
            if (modifiedQuery != null && !modifiedQuery.trim().isEmpty() && !modifiedQuery.equals(unsafeQuery)) {
                // 3. 수정된 쿼리의 행 수 계산
                log.info("3단계: 수정된 쿼리의 행 수 계산 시작");
                String modifiedCountResult = queryRequest.countRows(modifiedQuery, LIMIT);

                log.info("수정된 쿼리 countRows API 응답: {}", modifiedCountResult);
                
                int modifiedTotalRows = 0;
                try {
                    modifiedTotalRows = Integer.parseInt(modifiedCountResult);
                    log.info("수정된 쿼리 파싱된 총 행 수: {}", modifiedTotalRows);
                } catch (NumberFormatException e) {
                    log.warn("수정된 쿼리 행 수 파싱 실패: {}", modifiedCountResult);
                    modifiedTotalRows = 0;
                }
                
                // 4. hasNext 플래그 설정
                if (modifiedTotalRows > LIMIT) {
                    state.setHasNext(true);
                    log.info("✅ 수정된 쿼리에서 다음 페이지가 존재합니다. 총 행 수: {}, LIMIT: {}", modifiedTotalRows, LIMIT);
                    
                    // LIMIT 추가된 쿼리로 수정
                    log.info("4단계: 수정된 쿼리에 LIMIT 추가 시작");
                    String limitedModifiedQuery = queryRequest.addLimits(modifiedQuery, LIMIT, 0);
                    log.info("LIMIT 추가된 수정된 쿼리: {}", limitedModifiedQuery);
                    modifiedQuery = limitedModifiedQuery;
                } else {
                    state.setHasNext(false);
                    log.info("❌ 수정된 쿼리에서 다음 페이지가 없습니다. 총 행 수: {}, LIMIT: {}", modifiedTotalRows, LIMIT);
                }
                
                // 5. 수정된 쿼리 실행
                log.info("5단계: 수정된 쿼리 실행 시작");
                log.info("실행할 쿼리: {}", modifiedQuery);
                
                List<Map<String, Object>> queryResult = mainJdbcTemplate.queryForList(modifiedQuery);
                List<String> columnList = extractColumns(modifiedQuery, queryResult);

                log.info("수정된 쿼리 실행 완료: {} 행 반환", queryResult.size());
                log.info("반환된 컬럼: {}", columnList);
                
                // 6. 상태 업데이트
                state.setSqlQuery(modifiedQuery);
                state.setTotalRows(modifiedTotalRows);
                state.setQueryResult(queryResult);
                state.setColumnList(columnList);
                state.setQueryResultStatus("success");
                state.setQueryChanged(true);
                
                            log.info("쿼리 수정 및 실행 완료 - 수정된 쿼리: {}", modifiedQuery);
            log.info("최종 상태 - hasNext: {}, totalRows: {}, queryResultSize: {}, safeCount: {}", 
                    state.getHasNext(), state.getTotalRows(), queryResult.size(), state.getSafeCount());
            
            // WebSocket 메시지 전송 (node.py의 safeguard 참고)
            Map<String, Object> data = new HashMap<>();
            data.put("sql_query", modifiedQuery);
            webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "safeguard", data);
        } else {
            log.warn("쿼리가 수정되지 않았거나 빈 결과입니다.");
            state.setQueryChanged(false);
        }
        
        log.info("=== SafeguardNode 실행 완료 ===");

        } catch (Exception e) {
            log.error("❌ SafeguardNode 실행 중 예외 발생: {}", e.getMessage(), e);
            state.setQueryChanged(false);
            state.setQueryResultStatus("failed");
            state.setSqlError("Safeguard 쿼리 실행 실패: " + e.getMessage());
            state.setQueryError(true);
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("SAFEGUARD_ERROR", e.getMessage()));
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