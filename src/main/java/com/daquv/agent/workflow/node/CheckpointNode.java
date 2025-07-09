package com.daquv.agent.workflow.node;

import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.WebSocketUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@Component
public class CheckpointNode implements WorkflowNode {

    @Value("${api.vector-store-domain}")
    private String vectorStoreDomain;

    @Autowired
    private RestTemplate restTemplate;
    
    @Autowired
    private WebSocketUtils webSocketUtils;

    @Override
    public String getId() {
        return "checkpoint";
    }

    @Override
    public void execute(WorkflowState state) {
        String userQuestion = state.getUserQuestion();

        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("사용자 질문이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다."));
            return;
        }

        try {
            // 벡터 스토어 API 호출하여 joy/fin 분류
            String classification = classifyJoy(userQuestion);
            
            if ("joy".equals(classification)) {
                log.info("일상 대화로 분류됨: {}", userQuestion);
                state.setIsJoy(true);
            } else {
                log.info("금융 관련 질문으로 분류됨: {}", userQuestion);
                state.setIsJoy(false);
            }
            
        } catch (Exception e) {
            log.error("분류 중 오류 발생: {}", e.getMessage(), e);
            // 에러 시 기본값은 금융 관련 질문으로 설정
            state.setIsJoy(false);
            // 에러가 발생해도 워크플로우는 계속 진행
        }
        
        // WebSocket 메시지 전송 (checkpoint는 단순 분류이므로 시작 메시지만)
        webSocketUtils.sendNodeStart(state.getWebSocketSession(), "checkpoint");
    }
    


    private String classifyJoy(String queryText) {
        try {
            String url = vectorStoreDomain + "/checkpoint/" + sanitizeQuery(queryText);
            
            // 요청 헤더 설정
//            HttpHeaders headers = new HttpHeaders();
//            headers.setContentType(MediaType.APPLICATION_JSON);
            
            // 요청 본문 설정
//            Map<String, String> payload = new HashMap<>();
//            payload.put("query_text", sanitizeQuery(queryText));
            
//            HttpEntity<Map<String, String>> request = new HttpEntity<>(payload, headers);
            
            // API 호출
            Map<String, Object> response = restTemplate.getForObject(url, Map.class);
            
            if (response != null && response.containsKey("checkpoint")) {
                String classification = (String) response.get("checkpoint");
                log.info("분류 결과: {}", classification);
                return classification;
            } else {
                log.warn("분류 결과가 없습니다. 기본값 'fin' 사용");
                return "fin";
            }
            
        } catch (Exception e) {
            log.error("벡터 스토어 API 호출 중 오류: {}", e.getMessage(), e);
            return "fin"; // 기본값은 금융 관련 질문
        }
    }

    private String sanitizeQuery(String queryText) {
        // 슬래시, 백슬래시, 따옴표 등 URL에 문제가 될 수 있는 특수 문자를 언더스코어로 변환
        return queryText.replaceAll("[\\\\/\"'&?#]", "-");
    }
} 