package com.daquv.agent.quvi.logging;

import com.daquv.agent.quvi.dto.ChainLogEntry;
import com.daquv.agent.quvi.dto.LogAlertRule;
import com.daquv.agent.quvi.logging.ChainLogContext;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import javax.annotation.PostConstruct;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * 로그 알림 서비스
 */
@Slf4j
@Service
public class LogAlertService {

    private final RestTemplate restTemplate;
    private final String flowApiUrl;
    private final String flowApiKey;
    private final String registerEmail;

    public LogAlertService(RestTemplate restTemplate,
                           @Value("${flow.api.url:}") String flowApiUrl,
                           @Value("${flow.api.key:}") String flowApiKey,
                           @Value("${flow.register.email:silicao3o@daquv.com}") String registerEmail,
                           @Value("${flow.project.id:0}") Long projectId) {
        this.restTemplate = restTemplate;
        this.flowApiUrl = flowApiUrl;
        this.flowApiKey = flowApiKey;
        this.registerEmail = registerEmail;

    }

    /**
     * 체인 에러 전용 알림 전송
     */
    public void sendChainErrorAlert(LogAlertRule rule, String chainId, ChainLogContext context,
                                    ChainLogEntry entry, String chainLogText) {
        log.info("🚨 체인 에러 알림 전송 시작 - chainId: {}", chainId);

        CompletableFuture.runAsync(() -> {
            try {
                sendFlowChainErrorAlert(rule, chainId, context, entry, chainLogText);
                log.info("✅ 체인 에러 Flow 알림 전송 성공 - chainId: {}", chainId);
            } catch (Exception e) {
                log.error("❌ 체인 에러 Flow 알림 전송 실패 - chainId: {}, error: {}", chainId, e.getMessage(), e);
            }
        });
    }

    /**
     * Flow API로 체인 에러 알림 전송
     */
    private void sendFlowChainErrorAlert(LogAlertRule rule, String chainId, ChainLogContext context,
                                         ChainLogEntry entry, String chainLogText) {
        if (flowApiKey == null || flowApiKey.isEmpty()) {
            log.debug("Flow API Key가 설정되지 않았습니다.");
            return;
        }

        try {
            // 제목 생성
            String title = String.format("🚨 [%s] 체인 실행 실패 - %s",
                    context.getUserInfo() != null ? context.getUserInfo().getCompanyId() : "UNKNOWN",
                    chainId);

            // 내용 생성 (chain_id와 chain_log 중심)
            String contents = buildChainErrorContents(chainId, context, chainLogText);

            // Flow API 요청 본문 생성
            Map<String, Object> body = new HashMap<>();
            body.put("registerId", registerEmail);
            body.put("title", title);
            body.put("contents", contents);
            // body.put("status", "request");

            // HTTP 헤더 설정
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("x-flow-api-key", flowApiKey);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);
            RestTemplate restTemplate = new RestTemplate();

            log.info("📤 체인 에러 Flow API 요청 전송 중...");
            try {
                ResponseEntity<String> response = restTemplate.postForEntity(flowApiUrl, entity, String.class);

                log.info("✅ Flow API 응답 성공:");
                log.info("  - Status Code: {}", response.getStatusCode());
                log.info("  - Response Headers: {}", response.getHeaders());
                log.info("  - Response Body: {}", response.getBody());

            } catch (Exception requestException) {
                log.error("❌ Flow API 요청 실패:");
                log.error("  - Exception Type: {}", requestException.getClass().getSimpleName());
                log.error("  - Exception Message: {}", requestException.getMessage());

                // HTTP 에러인 경우 상세 정보 로깅
                if (requestException instanceof org.springframework.web.client.HttpClientErrorException) {
                    org.springframework.web.client.HttpClientErrorException httpError =
                            (org.springframework.web.client.HttpClientErrorException) requestException;
                    log.error("  - HTTP Status: {}", httpError.getStatusCode());
                    log.error("  - Response Headers: {}", httpError.getResponseHeaders());
                    log.error("  - Response Body: {}", httpError.getResponseBodyAsString());
                }

                throw requestException;
            }

            log.info("✅ 체인 에러 Flow 알림 전송 성공 - chainId: {}", chainId);

        } catch (Exception e) {
            log.error("체인 에러 Flow 알림 전송 실패 - chainId: {}, error: {}", chainId, e.getMessage(), e);
            throw e;
        }
    }

    /**
     * 체인 에러 알림 내용 생성 (chain_id와 chain_log 중심)
     */
    private String buildChainErrorContents(String chainId, ChainLogContext context, String chainLogText) {
        StringBuilder contents = new StringBuilder();

        // 기본 정보
        contents.append("체인 실행 실패 알림\n\n");
        contents.append("체인 정보\n");
        contents.append("Chain ID: ").append(chainId).append("\n");
        contents.append("User ID: ").append(context.getUserId()).append("\n");

        if (context.getUserInfo() != null && context.getUserInfo().getCompanyId() != null) {
            contents.append("Company ID: ").append(context.getUserInfo().getCompanyId()).append("\n");
        }

        contents.append("Question: ").append(context.getUserQuestion()).append("\n");
        contents.append("Duration: ").append(context.getDurationMs()).append("ms\n");
        contents.append("Session ID: ").append(context.getConversationId()).append("\n\n");

        contents.append("Chain Log:\n");
        contents.append("```\n");
        String truncatedLog = chainLogText;
        if (chainLogText.length() > 4000) {
            truncatedLog = chainLogText.substring(0, 4000) + "\n\n... (로그가 길어서 축약됨)";
        }

        contents.append(truncatedLog);
        contents.append("```\n");

        return contents.toString();
    }
    /**
     * 서비스 시작 시 설정 검증
     */
    @PostConstruct
    public void validateConfiguration() {
        log.info("🔧 LogAlertService 설정 검증");
        log.info("  - flowApiUrl: {}", flowApiUrl);
        log.info("  - flowApiKey 설정됨: {}", flowApiKey != null && !flowApiKey.isEmpty());
        log.info("  - flowApiKey 길이: {}", flowApiKey != null ? flowApiKey.length() : 0);
        log.info("  - flowApiKey : {}", flowApiKey);
        log.info("  - registerEmail: {}", registerEmail);

        if (flowApiKey == null || flowApiKey.isEmpty()){
            log.warn("⚠️ application.yml에서 flow.api.key 값을 확인해주세요.");
        }

        if (flowApiKey != null && !flowApiKey.isEmpty()) {
            log.info("✅ Flow 알림 설정이 완료되었습니다.");
        }
    }
}