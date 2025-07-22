package com.daquv.agent.workflow.node;

import com.daquv.agent.quvi.requests.QueryRequest;
import com.daquv.agent.quvi.util.*;
import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.workflow.dto.VectorNotes;
import com.daquv.agent.workflow.util.NameModifierUtils;
import com.daquv.agent.workflow.util.QueryUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
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
    
    private static final int LIMIT = 100;
    
    @Autowired
    @Qualifier("mainJdbcTemplate")
    private JdbcTemplate mainJdbcTemplate;
    
    @Autowired
    private WebSocketUtils webSocketUtils;
    
    @Autowired
    private QueryUtils queryUtils;

    @Autowired
    private NameModifierUtils nameModifierUtils;

    @Autowired
    private QueryRequest queryRequest;

    @Value("${view-table.dialect}")
    private String DIALECT;

    @Override
    public String getId() {
        return "executor";
    }

    @Override
    public void execute(WorkflowState state) {
        String rawQuery = state.getSqlQuery();
        String companyId = state.getUserInfo().getCompanyId();
        String workflowId = state.getWorkflowId();
        List<Map<String, Object>> queryResult = new ArrayList<>();
        List<String> columnList = new ArrayList<>();

        if (state.getSafeCount() == null) {
            state.setSafeCount(0);
        }

        if (rawQuery == null || rawQuery.trim().isEmpty()) {
            log.error("SQL 쿼리가 비어있습니다.");
            state.setQueryResultStatus("failed");
            state.setSqlError("SQL 쿼리가 비어있습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("SQL_ERROR", "SQL 쿼리가 비어있습니다."));
            return;
        }

        try {
            log.info("=== QueryExecutorNode 실행 시작 ===");
            log.info("원본 SQL 쿼리: {}", rawQuery);
            log.info("LIMIT 값: {}", LIMIT);
            
            if (state.getIsApi()) {
                // API 쿼리 처리

                log.info("API 쿼리용 chainId 설정: {}", workflowId);
                DatabaseProfilerAspect.setWorkflowId(workflowId);
                queryResult = mainJdbcTemplate.queryForList(rawQuery);
                log.info("API 쿼리 완료, 반환 행 수: {}", queryResult.size());
                
                if (!queryResult.isEmpty()) {
                    Map<String, Object> data = new HashMap<>();
                    data.put("result_row", queryResult.size());
                    data.put("result_column", queryResult.get(0).keySet().size());
                    webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "executor", data);
                }
                
                state.setSqlQuery(rawQuery);
                state.setQueryResult(queryResult);
                
                if (queryResult.isEmpty()) {
                    state.setNoData(true);
                }
                
            } else {
                // 일반 쿼리 처리
                String selectedTable = state.getSelectedTable();
                
                // 1. 권한 있는 회사/계좌 검사
                String queryRightCom = queryUtils.addComCondition(rawQuery, companyId);
                
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
                
                // 5. 행 수 계산 및 페이지네이션
                String countResult;
                log.info("COUNT 쿼리용 chainId 설정: {}", workflowId);
                DatabaseProfilerAspect.setWorkflowId(workflowId);
                countResult = queryRequest.countRows(viewQuery, LIMIT);
                log.info("COUNT 쿼리 완료");

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
                
                if (totalRows > LIMIT) {
                    log.info("✅ 다음 페이지가 존재합니다. 총 행 수: {}, LIMIT: {}", totalRows, LIMIT);
                    log.info("2단계: LIMIT 추가된 쿼리 생성 시작");
                    state.setHasNext(true);
                    viewQuery = queryRequest.addLimits(viewQuery, LIMIT, 0);
                    log.info("LIMIT 추가된 쿼리: {}", viewQuery);
                } else {
                    state.setHasNext(false);
                    log.info("❌ 다음 페이지가 없습니다. 총 행 수: {}, LIMIT: {}", totalRows, LIMIT);
                }

                log.info("최종 hasNext 상태: {}", state.getHasNext());

                log.info("3단계: 실제 DB 쿼리 실행 시작");
                log.info("실행할 쿼리: {}", viewQuery);
                
                // 6. 쿼리 실행

                log.info("메인 쿼리용 chainId 설정: {}", workflowId);
                DatabaseProfilerAspect.setWorkflowId(workflowId);
                queryResult = mainJdbcTemplate.queryForList(viewQuery);
                log.info("메인 쿼리 완료, 반환 행 수: {}", queryResult.size());

                
                if (!queryResult.isEmpty()) {
                    Map<String, Object> data = new HashMap<>();
                    List<String> resultColumn = extractColumns(viewQuery, queryResult);
                    data.put("result_row", queryResult.size());
                    data.put("result_column", resultColumn);
                    webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "executor", data);
                }

                state.setSqlQuery(viewQuery);
                
                // 7. note1 조건 확인 및 vector search
                try {
                    List<String> noteConditions = queryUtils.findColumnConditions(viewQuery, "note1");
                    
                    if ((queryResult.isEmpty() || queryUtils.isNullOnly(queryResult)) && !noteConditions.isEmpty()) {
                        Map<String, Object> evernoteResult = queryUtils.everNote(viewQuery, workflowId);
                        
                        List<String> originNote = (List<String>) evernoteResult.get("origin_note");
                        List<String> vectorNotes = (List<String>) evernoteResult.get("vector_notes");
                        String modifiedQuery = (String) evernoteResult.get("query");
                        
                        if (vectorNotes != null && !vectorNotes.isEmpty()) {
                            log.info("Found {} similar notes", vectorNotes.size());
                            
                            // vector notes 데이터 저장
                            VectorNotes vectorNotesObj = VectorNotes.builder()
                                .originNote(originNote)
                                .vectorNotes(vectorNotes)
                                .build();
                            state.setVectorNotes(vectorNotesObj);
                            
                            // final_answer 업데이트
                            String originNoteStr = String.join("', '", originNote);
                            String vectorNoteStr = String.join("', '", vectorNotes);
                            String finalAnswer = String.format(
                                "요청을 처리하기 위해 '%s' 노트의 거래내역을 찾아 보았으나 검색된 결과가 없었습니다. 해당 기간 거래내역의 노트 중 유사한 노트('%s')로 검색한 결과는 다음과 같습니다.",
                                originNoteStr, vectorNoteStr
                            );
                            state.setFinalAnswer(finalAnswer);
                            state.setNoteChanged(true);
                        }
                        
                        // 수정된 쿼리로 재실행
                        if (modifiedQuery != null && !modifiedQuery.equals(viewQuery)) {

                            log.info("수정된 쿼리용 chainId 설정: {}", workflowId);
                            DatabaseProfilerAspect.setWorkflowId(workflowId);
                            queryResult = mainJdbcTemplate.queryForList(modifiedQuery);
                            log.info("수정된 쿼리 완료, 반환 행 수: {}", queryResult.size());

                            state.setSqlQuery(modifiedQuery);
                        }
                        columnList = extractColumns(modifiedQuery, queryResult);
                    }
                } catch (Exception e) {
                    log.error("note 조건 확인 중 오류 발생: {}", e.getMessage());
                }
            }
            
            // 결과가 없는 경우 처리
            if (queryResult.isEmpty() || queryUtils.isNullOnly(queryResult)) {
                log.warn("쿼리 결과에 데이터가 없습니다");
                state.setNoData(true);
                queryResult = new ArrayList<>();
                state.setQueryResult(queryResult);
                return;
            }

            log.info("쿼리 실행 성공, 결과 저장");
            state.setQueryResult(queryResult);
            state.setColumnList(columnList);
            state.setQueryResultStatus("success");

            // WebSocket 메시지 전송 (node.py의 executor 참고)
            Map<String, Object> data = new HashMap<>();
            data.put("result_row", queryResult.size());
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