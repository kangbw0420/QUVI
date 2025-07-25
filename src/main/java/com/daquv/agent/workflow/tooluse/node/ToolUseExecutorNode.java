package com.daquv.agent.workflow.tooluse.node;

import com.daquv.agent.quvi.requests.QueryRequest;
import com.daquv.agent.quvi.util.*;
import com.daquv.agent.workflow.tooluse.ToolUseWorkflowNode;
import com.daquv.agent.workflow.tooluse.ToolUseWorkflowState;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class ToolUseExecutorNode implements ToolUseWorkflowNode {

    private static final int LIMIT = 100;

    @Autowired
    @Qualifier("mainJdbcTemplate")
    private JdbcTemplate mainJdbcTemplate;

    @Autowired
    private WebSocketUtils webSocketUtils;

    @Autowired
    private QueryRequest queryRequest;

    @Autowired
    private RequestProfiler requestProfiler;

    @Override
    public String getId() {
        return "tooluse_executor";
    }

    @Override
    public void execute(ToolUseWorkflowState state) {
        String rawQuery = state.getSqlQuery();
        String workflowId = state.getWorkflowId();
        List<Map<String, Object>> queryResult = new ArrayList<>();

        if (rawQuery == null || rawQuery.trim().isEmpty()) {
            log.error("ToolUse: SQL 쿼리가 비어있습니다.");
            state.setQueryResultStatus("failed");
            state.setSqlError("SQL 쿼리가 비어있습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("SQL_ERROR", "SQL 쿼리가 비어있습니다."));
            return;
        }

        try {
            log.info("=== ToolUse QueryExecutorNode 실행 시작 ===");
            log.info("API 쿼리: {}", rawQuery);
            log.info("LIMIT 값: {}", LIMIT);

            // API 쿼리는 권한/매핑 변환 없이 직접 실행
            log.info("API 쿼리용 workflowId 설정: {}", workflowId);
            DatabaseProfilerAspect.setWorkflowId(workflowId);

            // 1. 행 수 계산
            String countResult = queryRequest.countRows(rawQuery, LIMIT);
            log.info("ToolUse countRows API 응답: {}", countResult);

            int totalRows = 0;
            try {
                totalRows = Integer.parseInt(countResult);
                log.info("ToolUse 파싱된 총 행 수: {}", totalRows);
            } catch (NumberFormatException e) {
                log.warn("ToolUse 행 수 파싱 실패: {}", countResult);
                totalRows = 0;
            }

            state.setTotalRows(totalRows);

            // 2. 페이지네이션 처리
            String finalQuery = rawQuery;
            if (totalRows > LIMIT) {
                log.info("✅ ToolUse 다음 페이지가 존재합니다. 총 행 수: {}, LIMIT: {}", totalRows, LIMIT);
                state.setHasNext(true);
                finalQuery = queryRequest.addLimits(rawQuery, LIMIT, 0);
                log.info("ToolUse LIMIT 추가된 쿼리: {}", finalQuery);
            } else {
                state.setHasNext(false);
                log.info("❌ ToolUse 다음 페이지가 없습니다. 총 행 수: {}, LIMIT: {}", totalRows, LIMIT);
            }

            log.info("ToolUse 최종 hasNext 상태: {}", state.getHasNext());

            // 3. 실제 쿼리 실행
            log.info("ToolUse 실제 DB 쿼리 실행 시작");
            log.info("ToolUse 실행할 쿼리: {}", finalQuery);

            queryResult = mainJdbcTemplate.queryForList(finalQuery);
            log.info("ToolUse 쿼리 완료, 반환 행 수: {}", queryResult.size());

            // 4. 결과 처리
            if (queryResult.isEmpty()) {
                log.warn("ToolUse 쿼리 결과에 데이터가 없습니다");
                state.setNoData(true);
                queryResult = new ArrayList<>();
                state.setQueryResult(queryResult);
                return;
            }

            log.info("ToolUse 쿼리 실행 성공, 결과 저장");
            state.setSqlQuery(finalQuery);
            state.setQueryResult(queryResult);
            state.setQueryResultStatus("success");

            // WebSocket 메시지 전송
            Map<String, Object> data = new HashMap<>();
            data.put("result_row", queryResult.size());
            data.put("result_column", queryResult.isEmpty() ? 0 : queryResult.get(0).keySet().size());
            webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "tooluse_executor", data);

            log.info("=== ToolUse QueryExecutorNode 실행 완료 ===");
            log.info("ToolUse 최종 상태 - hasNext: {}, totalRows: {}, queryResultSize: {}",
                    state.getHasNext(), state.getTotalRows(), queryResult.size());

        } catch (Exception e) {
            log.error("❌ ToolUse QueryExecutorNode 실행 중 예외 발생: {}", e.getMessage(), e);
            state.setQueryResultStatus("failed");
            state.setSqlError("ToolUse 쿼리 실행 실패: " + e.getMessage());
            state.setQueryError(true);
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("TOOLUSE_QUERY_EXECUTION_ERROR", e.getMessage()));
        }
    }
}