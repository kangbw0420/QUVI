package com.daquv.agent.workflow.tooluse.node;

import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.util.WebSocketUtils;
import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.workflow.tooluse.ToolUseWorkflowNode;
import com.daquv.agent.workflow.tooluse.ToolUseWorkflowState;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

@Component
@Slf4j
public class YqmdNode implements ToolUseWorkflowNode {
    @Value("${api.vector-store-domain}")
    private String vectorStoreDomain;

    @Autowired
    private RestTemplate restTemplate;

    @Autowired
    private WebSocketUtils webSocketUtils;

    @Autowired
    private RequestProfiler requestProfiler;

    @Override
    public String getId() {
        return "yqmd";
    }

    @Override
    public void execute(ToolUseWorkflowState state) {
        String userQuestion = state.getUserQuestion();
        String sqlQuery = state.getSqlQuery();
        String workflowId = state.getWorkflowId();

        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("사용자 질문이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다."));
            return;
        }

        if (sqlQuery == null || sqlQuery.trim().isEmpty()) {
            log.error("SQL 쿼리가 비어있습니다.");
            state.setQueryResultStatus("failed");
            state.setSqlError("SQL 쿼리가 비어있습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("SQL_ERROR", "SQL 쿼리가 비어있습니다."));
            return;
        }

        // 벡터 스토어 API 호출하여 YQMD 분류
        String classification = classifyYqmd(userQuestion, sqlQuery, workflowId);
        state.setSqlQuery(classification);

        // WebSocket 메시지 전송 (yqmd는 단순 분류이므로 시작 메시지만)
        webSocketUtils.sendNodeStart(state.getWebSocketSession(), "yqmd");
    }

    private String classifyYqmd(String userQuestion, String sqlQuery, String chainId) {
        String classification;
        long startTime = System.currentTimeMillis();

        try {
            String sanitizedQuery = sanitizeQuery(userQuestion);
            String url = vectorStoreDomain + "/yqmd/" + sanitizedQuery;

            Map<String, Object> response = restTemplate.getForObject(url, Map.class);

            if (response != null && response.containsKey("yqmd")) {
                classification = (String) response.getOrDefault("yqmd", "m");
                log.info("YQMD 분류 결과: {}", classification);
            } else {
                log.warn("YQMD 분류 결과가 없습니다. 기본 값 'm' 사용.");
                classification = "m";
            }
        } catch (HttpClientErrorException e) {
            log.error("YQMD 분류 중 에러 from API: {}. 기본 값 'M' 사용.", e.getMessage());
            classification = "M";
            return appendParameterToQuery(sqlQuery, classification.toUpperCase());
        } catch (Exception e) {
            log.error("YQMD 분류 중 알수 없는 에러: {}. 기본 값 'M' 사용.", e.getMessage(), e);
            classification = "M";
            return appendParameterToQuery(sqlQuery, classification.toUpperCase());
        } finally {
            // 벡터 DB 프로파일링 기록
            long endTime = System.currentTimeMillis();
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordVectorDbCall(chainId, elapsedTime, "yqmd");
        }

        // 분류된 값을 대문자로 변환하여 쿼리에 추가
        return appendParameterToQuery(sqlQuery, classification.toUpperCase());
    }

    private String appendParameterToQuery(String sqlQuery, String parameter) {
        String trimmedQuery = sqlQuery.trim();
        if (trimmedQuery.endsWith(")")) {
            int lastParenIndex = trimmedQuery.lastIndexOf(')');
            return trimmedQuery.substring(0, lastParenIndex) + String.format(", '%s')", parameter);
        } else {
            log.warn("Query does not end with ')', couldn't add YQMD parameter. Returning original query.");
            return sqlQuery;
        }
    }

    private String sanitizeQuery(String userQuestion) {
        // 슬래시, 백슬래시, 따옴표 등 URL에 문제가 될 수 있는 특수 문자를 언더스코어로 변환
        return userQuestion.replaceAll("[\\\\/\"'&?#]", "-");
    }
}