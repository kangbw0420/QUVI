package com.daquv.agent.workflow.node;

import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.util.WebSocketUtils;
import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

@Slf4j
@Component
public class IsApiNode implements WorkflowNode {
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
        return "isapi";
    }

    @Override
    public void execute(WorkflowState state) {
        String userQuestion = state.getUserQuestion();
        String chainId = state.getChainId();

        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("사용자 질문이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다."));
            return;
        }

        try {
            // 벡터 스토어 API 호출하여 isApi/isNotApi 분류
            String classification = classifyApi(userQuestion, chainId);

            if ("1".equals(classification)) {
                log.info("isApi로 분류 됨: {}", userQuestion);
                state.setIsApi(true);
            } else {
                log.info("isNotApi로 분류 됨: {}", userQuestion);
                state.setIsApi(false);
            }

        } catch (Exception e) {
            log.error("분류 중 오류 발생: {}", e.getMessage(), e);
            // 에러 시 기본값은 isNotApi 질문으로 설정
            state.setIsApi(false);
            // 에러가 발생해도 워크플로우는 계속 진행
        }

        // WebSocket 메시지 전송 (isapi는 단순 분류이므로 시작 메시지만)
        webSocketUtils.sendNodeStart(state.getWebSocketSession(), "isapi");
    }

    private String classifyApi(String userQuestion, String chainId) {
        long startTime = System.currentTimeMillis();

        try {
            String url = vectorStoreDomain + "/isapi/" + sanitizeQuery(userQuestion);

            // API 호출
            Map<String, Object> response = restTemplate.getForObject(url, Map.class);

            if (response != null && response.containsKey("isapi")) {
                String classification = (String) response.get("isapi");
                log.info("분류 결과: {}", classification);
                return classification;
            } else {
                log.warn("분류 결과가 없습니다. 기본값 '0' 사용");
                return "0";
            }

        } catch (Exception e) {
            log.error("벡터 스토어 API 호출 중 오류: {}", e.getMessage(), e);
            return "0"; // 기본값은 isNotApi
        } finally {
            // 벡터 DB 프로파일링 기록
            long endTime = System.currentTimeMillis();
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordVectorDbCall(chainId, elapsedTime, "isapi");
        }
    }

    private String sanitizeQuery(String userQuestion) {
        // 슬래시, 백슬래시, 따옴표 등 URL에 문제가 될 수 있는 특수 문자를 언더스코어로 변환
        return userQuestion.replaceAll("[\\\\/\"'&?#]", "-");
    }
}