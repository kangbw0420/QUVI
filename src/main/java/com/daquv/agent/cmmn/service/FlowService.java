package com.daquv.agent.cmmn.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@Component
public class FlowService {

    @Value("${flow.project.id}")
    private String flowProjectId;

    @Value("${flow.api.key}")
    private String flowApiKey;

    @Value("${admin.email}")
    private String adminEmail;

    private final RestTemplate restTemplate;

    public FlowService() {
        this.restTemplate = new RestTemplate();
    }

    /**
     * DB 수정 요청을 Flow에 전송합니다.
     */
    public ResponseEntity<String> postTaskDb(String userId, String changeReason,
                                             String reportReasonDetail, String sqlQuery) {
        try {
            String apiUrl = String.format("https://api.flow.team/v1/posts/projects/%s/tasks", flowProjectId);

            String title = "[DB 수정]QVC Database 추가/수정/삭제 요청";
            String contents = String.format(
                    "아이디 : %s\n\n" +
                            "변경 요청 사유 : %s\n\n" +
                            "상세요청 : %s\n\n" +
                            "Query : %s\n\n",
                    userId,
                    changeReason != null ? changeReason : "N/A",
                    reportReasonDetail,
                    sqlQuery
            );

            Map<String, Object> body = new HashMap<>();
            body.put("registerId", adminEmail);
            body.put("title", title);
            body.put("contents", contents);
            body.put("status", "request");

            log.info("[FLOW] body : {}", body);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("x-flow-api-key", flowApiKey);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);

            ResponseEntity<String> response = restTemplate.postForEntity(apiUrl, entity, String.class);
            log.info("Flow 응답: {}", response.getBody());

            return response;

        } catch (Exception e) {
            log.error("Flow 알림 전송 중 오류: {}", e.getMessage(), e);
            throw new RuntimeException("Flow 알림 전송 실패: " + e.getMessage(), e);
        }
    }

    /**
     * 질문 신고를 Flow에 전송합니다.
     */
    public ResponseEntity<String> postTask(String userId, String question, String answer,
                                           String sqlQuery, String reportReason, String reportReasonDetail) {
        try {
            String apiUrl = String.format("https://api.flow.team/v1/posts/projects/%s/tasks", flowProjectId);

            String title = String.format("[질문신고]%s", question);
            String contents = String.format(
                    "아이디 : %s\n\n" +
                            "질문내용 : %s\n\n" +
                            "답변내용 : %s\n\n" +
                            "Query : %s\n\n" +
                            "----------------------------------------------------------------------\n\n" +
                            "신고이유 : %s\n" +
                            "상세의견 : %s\n",
                    userId, question, answer, sqlQuery, reportReason, reportReasonDetail
            );

            Map<String, Object> body = new HashMap<>();
            body.put("registerId", adminEmail);
            body.put("title", title);
            body.put("contents", contents);
            body.put("status", "request");

            log.info("[FLOW] body : {}", body);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("x-flow-api-key", flowApiKey);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);

            ResponseEntity<String> response = restTemplate.postForEntity(apiUrl, entity, String.class);
            log.info("Flow 응답: {}", response.getBody());

            return response;

        } catch (Exception e) {
            log.error("Flow 알림 전송 중 오류: {}", e.getMessage(), e);
            throw new RuntimeException("Flow 알림 전송 실패: " + e.getMessage(), e);
        }
    }
}