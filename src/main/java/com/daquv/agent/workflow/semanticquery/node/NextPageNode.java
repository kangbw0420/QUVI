package com.daquv.agent.workflow.semanticquery.node;

import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.llmadmin.HistoryService;
import com.daquv.agent.quvi.requests.QueryRequest;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.WebSocketUtils;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowNode;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component("semanticQueryNextPageNode")
public class NextPageNode implements SemanticQueryWorkflowNode {

    private static final int LIMIT = 100;

    @Autowired
    private HistoryService historyService;

    @Autowired
    @Qualifier("mainJdbcTemplate")
    private JdbcTemplate mainJdbcTemplate;

    private final QueryRequest queryRequest;

    @Autowired
    private WebSocketUtils webSocketUtils;

    @Autowired
    private RequestProfiler requestProfiler;

    public NextPageNode(QueryRequest queryRequest) {
        this.queryRequest = queryRequest;
    }

    @Override
    public String getId() {
        return "next_page";
    }

    @Override
    public void execute(SemanticQueryWorkflowState state) {
        log.info("=== NextPageNode 실행 시작 ===");

        try {
            String userQuestion = state.getUserQuestion();
            String workflowId = state.getWorkflowId();

            log.info("사용자 질문: {}", userQuestion);
            log.info("워크플로우 ID: {}", workflowId);

            // "next_page" 요청인지 확인
            if (!"next_page".equals(userQuestion)) {
                log.info("next_page 요청이 아니므로 건너뜁니다.");
                return;
            }

            log.info("✅ next_page 요청 감지 - 페이지네이션 처리 시작");

            // SemanticQueryExecution이 있는지 확인
            Map<String, SemanticQueryWorkflowState.SemanticQueryExecution> executionMap =
                    state.getSemanticQueryExecutionMap();

            if (executionMap == null || executionMap.isEmpty()) {
                log.warn("SemanticQueryExecution이 없습니다.");
                state.setFinalAnswer("이전 쿼리가 없어 페이지네이션을 수행할 수 없습니다.");
                return;
            }

            // 각 entity의 execution에 대해 next page 처리
            int totalExecutionsProcessed = 0;
            int totalQueriesExecuted = 0;

            for (Map.Entry<String, SemanticQueryWorkflowState.SemanticQueryExecution> entry : executionMap.entrySet()) {
                String entity = entry.getKey();
                SemanticQueryWorkflowState.SemanticQueryExecution execution = entry.getValue();

                log.debug("Processing next page for entity: '{}'", entity);

                // hasNext가 true인 경우에만 처리
                if (execution.getHasNext() == null || !execution.getHasNext()) {
                    log.debug("Entity '{}' has no next page, skipping", entity);
                    continue;
                }

                Map<String, String> sqlMap = execution.getSqlQuery();
                if (sqlMap == null || sqlMap.isEmpty()) {
                    log.warn("No SQL queries found for entity '{}', skipping", entity);
                    continue;
                }

                // 각 SQL 쿼리에 대해 next page 처리
                for (Map.Entry<String, String> sqlEntry : sqlMap.entrySet()) {
                    String queryKey = sqlEntry.getKey();
                    String recentQuery = sqlEntry.getValue();

                    if (recentQuery == null || recentQuery.trim().isEmpty()) {
                        log.warn("Empty SQL query for key '{}', skipping", queryKey);
                        continue;
                    }

                    log.info("Entity '{}', Query Key '{}': 페이지네이션 처리 시작", entity, queryKey);
                    log.info("최근 SQL 쿼리: {}", recentQuery);

                    // 페이지네이션 쿼리 생성
                    log.info("페이지네이션 쿼리 생성 시작");
                    String nextPageQuery = queryRequest.pagination(recentQuery, LIMIT);
                    log.info("페이지네이션 쿼리 생성: {}", nextPageQuery);

                    // 행 수 계산
                    log.info("페이지네이션 쿼리의 행 수 계산 시작");
                    String countResult = queryRequest.countRows(nextPageQuery, LIMIT);
                    log.info("countRows API 응답: {}", countResult);

                    int totalRows = 0;
                    try {
                        totalRows = Integer.parseInt(countResult);
                        log.info("파싱된 총 행 수: {}", totalRows);
                    } catch (NumberFormatException e) {
                        log.warn("행 수 파싱 실패: {}", countResult);
                        totalRows = 0;
                    }

                    // totalRows를 execution에 저장
                    execution.addTotalRows(queryKey + "_next", totalRows);

                    // hasNext 플래그 설정
                    if (totalRows > LIMIT) {
                        execution.setHasNext(true);
                        log.info("✅ 다음 페이지가 존재합니다. 총 행 수: {}, PAGE_SIZE: {}", totalRows, LIMIT);

                        // LIMIT 추가된 쿼리로 실행
                        String limitedNextPageQuery = queryRequest.addLimits(nextPageQuery, LIMIT, 0);
                        log.info("LIMIT 추가된 페이지네이션 쿼리: {}", limitedNextPageQuery);
                        nextPageQuery = limitedNextPageQuery;
                    } else {
                        execution.setHasNext(false);
                        log.info("❌ 다음 페이지가 없습니다. 총 행 수: {}, PAGE_SIZE: {}", totalRows, LIMIT);
                    }

                    // 실제 DB 쿼리 실행
                    log.info("페이지네이션 쿼리 실행 시작");
                    log.info("실행할 쿼리: {}", nextPageQuery);

                    List<Map<String, Object>> queryResult = mainJdbcTemplate.queryForList(nextPageQuery);
                    log.info("페이지네이션 쿼리 실행 완료: {} 행 반환", queryResult.size());

                    // 결과를 execution에 저장
                    execution.addSqlQuery(queryKey, nextPageQuery);
                    execution.addQueryResult(queryKey, queryResult);
                    execution.addTotalRows(queryKey, queryResult.size());

                    execution.setQueryResultStatus("success");
                    execution.setQueryError(false);

                    totalQueriesExecuted++;
                }

                totalExecutionsProcessed++;
                log.debug("Completed next page processing for entity '{}'. hasNext: {}",
                        entity, execution.getHasNext());
            }

            // 최종 상태 설정
            state.setFinalAnswer("다음 페이지 데이터입니다.");

            // WebSocket 메시지 전송
            Map<String, Object> data = new HashMap<>();
            data.put("processed_executions", totalExecutionsProcessed);
            data.put("total_queries_executed", totalQueriesExecuted);
            data.put("entities_processed", executionMap.keySet());
            webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "next_page", data);

            log.info("=== NextPageNode 실행 완료 ===");
            log.info("처리된 실행: {}, 처리된 쿼리: {}", totalExecutionsProcessed, totalQueriesExecuted);

        } catch (Exception e) {
            log.error("❌ NextPageNode 실행 중 예외 발생: {}", e.getMessage(), e);

            // 모든 execution에 에러 상태 설정
            if (state.getSemanticQueryExecutionMap() != null) {
                for (SemanticQueryWorkflowState.SemanticQueryExecution execution :
                        state.getSemanticQueryExecutionMap().values()) {
                    execution.setQueryResultStatus("failed");
                    execution.setSqlError("페이지네이션 처리 실패: " + e.getMessage());
                    execution.setQueryError(true);
                }
            }
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("PAGINATION_ERROR", e.getMessage()));
        }
    }
}