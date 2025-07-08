package com.daquv.agent.workflow.node;

import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.quvi.llmadmin.HistoryService;
import com.daquv.agent.quvi.requests.QueryRequest;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.WebSocketUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class NextPageNode implements WorkflowNode {

    private static final int LIMIT = 100; // 테스트용 LIMIT 값

    @Autowired
    private HistoryService historyService;
    
    @Autowired
    @Qualifier("mainJdbcTemplate")
    private JdbcTemplate mainJdbcTemplate;
    
    private final QueryRequest queryRequest;
    
    @Autowired
    private WebSocketUtils webSocketUtils;
    
    public NextPageNode(QueryRequest queryRequest) {
        this.queryRequest = queryRequest;
    }

    @Override
    public String getId() {
        return "next_page";
    }

    @Override
    public void execute(WorkflowState state) {
        log.info("=== NextPageNode 실행 시작 ===");
        
        try {
            String userQuestion = state.getUserQuestion();
            String chainId = state.getChainId();
            
            log.info("사용자 질문: {}", userQuestion);
            log.info("체인 ID: {}", chainId);
            
            // "next_page" 요청인지 확인
            if (!"next_page".equals(userQuestion)) {
                log.info("next_page 요청이 아니므로 건너뜁니다.");
                return;
            }
            
            log.info("✅ next_page 요청 감지 - 페이지네이션 처리 시작");
            
            // 최근 SQL 쿼리 조회
            log.info("1단계: 최근 SQL 쿼리 히스토리 조회");
            Object recentQueryObj = historyService.getRecentHistory(chainId, "sql_query");
            if (recentQueryObj == null) {
                log.warn("최근 SQL 쿼리 히스토리가 없습니다.");
                state.setFinalAnswer("이전 쿼리가 없어 페이지네이션을 수행할 수 없습니다.");
                return;
            }
            
            String recentQuery = (String) recentQueryObj;
            if (recentQuery == null || recentQuery.trim().isEmpty()) {
                log.warn("최근 SQL 쿼리가 비어있습니다.");
                state.setFinalAnswer("이전 쿼리가 없어 페이지네이션을 수행할 수 없습니다.");
                return;
            }
            
            log.info("최근 SQL 쿼리: {}", recentQuery);
            
            // 페이지네이션 쿼리 생성
            log.info("2단계: 페이지네이션 쿼리 생성 시작");
            log.info("LIMIT 값: {}", LIMIT);
            String nextPageQuery = queryRequest.pagination(recentQuery, LIMIT);
            log.info("페이지네이션 쿼리 생성: {}", nextPageQuery);
            
            // 행 수 계산
            log.info("3단계: 페이지네이션 쿼리의 행 수 계산 시작");
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
            
            state.setTotalRows(totalRows);
            log.info("WorkflowState에 설정된 총 행 수: {}", state.getTotalRows());
            
            // hasNext 플래그 설정
            if (totalRows > LIMIT) {
                state.setHasNext(true);
                log.info("✅ 다음 페이지가 존재합니다. 총 행 수: {}, LIMIT: {}", totalRows, LIMIT);
                
                // LIMIT 추가된 쿼리로 실행
                log.info("4단계: LIMIT 추가된 페이지네이션 쿼리 생성");
                String limitedNextPageQuery = queryRequest.addLimits(nextPageQuery, LIMIT, 0);
                log.info("LIMIT 추가된 페이지네이션 쿼리: {}", limitedNextPageQuery);
                nextPageQuery = limitedNextPageQuery;
            } else {
                state.setHasNext(false);
                log.info("❌ 다음 페이지가 없습니다. 총 행 수: {}, LIMIT: {}", totalRows, LIMIT);
            }
            
            log.info("최종 hasNext 상태: {}", state.getHasNext());
            
            // 실제 DB 쿼리 실행
            log.info("5단계: 페이지네이션 쿼리 실행 시작");
            log.info("실행할 쿼리: {}", nextPageQuery);
            
            List<Map<String, Object>> queryResult = mainJdbcTemplate.queryForList(nextPageQuery);

            log.info("페이지네이션 쿼리 실행 완료: {} 행 반환", queryResult.size());

            // 상태 업데이트
            state.setSqlQuery(nextPageQuery);
            state.setQueryResult(queryResult);
            state.setFinalAnswer("다음 페이지 데이터입니다.");
            state.setQueryResultStatus("success");
            
            log.info("=== NextPageNode 실행 완료 ===");
            log.info("최종 상태 - hasNext: {}, totalRows: {}, queryResultSize: {}", 
                    state.getHasNext(), state.getTotalRows(), queryResult.size());
            
            // WebSocket 메시지 전송 (next_page는 특별한 처리이므로 완료 메시지만)
            Map<String, Object> data = new HashMap<>();
            data.put("result_row", queryResult.size());
            webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "next_page", data);

        } catch (Exception e) {
            log.error("❌ NextPageNode 실행 중 예외 발생: {}", e.getMessage(), e);
            state.setQueryResultStatus("failed");
            state.setSqlError("페이지네이션 처리 실패: " + e.getMessage());
            state.setQueryError(true);
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("PAGINATION_ERROR", e.getMessage()));
        }
    }
} 