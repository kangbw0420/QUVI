package com.daquv.agent.quvi;

import com.daquv.agent.quvi.dto.LogLevel;
import com.daquv.agent.quvi.dto.QuviHilResumeDto;
import com.daquv.agent.quvi.llmadmin.WorkflowService;
import com.daquv.agent.quvi.logging.WorkflowLogContext;
import com.daquv.agent.quvi.logging.WorkflowLogManager;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.workflow.WorkflowExecutionManagerService;
import com.daquv.agent.workflow.dto.UserInfo;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.util.*;
import com.daquv.agent.quvi.util.StatisticsUtils;
import com.daquv.agent.quvi.util.ResponseUtils;

@Component
@Slf4j
public class ResumeWebSocketHandler extends TextWebSocketHandler {

    private final WorkflowService workflowService;
    private final WorkflowLogManager chainLogManager;
    private final RequestProfiler requestProfiler;
    private final ObjectMapper objectMapper;

    @Autowired
    private WorkflowExecutionManagerService workflowExecutionManagerService;

    public ResumeWebSocketHandler(WorkflowService workflowService, 
                                 WorkflowLogManager chainLogManager,
                                 RequestProfiler requestProfiler, 
                                 ObjectMapper objectMapper) {
        this.workflowService = workflowService;
        this.chainLogManager = chainLogManager;
        this.requestProfiler = requestProfiler;
        this.objectMapper = objectMapper;
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        try {
            String payload = message.getPayload();
            log.info("🔄 WebSocket HIL 재개 요청 수신: {}", payload);

            QuviHilResumeDto request = objectMapper.readValue(payload, QuviHilResumeDto.class);

            // WebSocket HIL 재개 처리 로직 실행
            Map<String, Object> response = processHilResumeRequest(request, session);

            // WebSocket으로 최종 응답 전송
            String responseJson = objectMapper.writeValueAsString(response);
            session.sendMessage(new TextMessage(responseJson));

            log.info("WebSocket HIL 재개 응답 전송 완료");

        } catch (Exception e) {
            log.error("❌ WebSocket HIL 재개 메시지 처리 중 예외 발생: {}", e.getMessage(), e);

            // 에러 응답 전송
            Map<String, Object> errorResponse = buildErrorResponse(e.getMessage());
            try {
                String errorJson = objectMapper.writeValueAsString(errorResponse);
                session.sendMessage(new TextMessage(errorJson));
            } catch (Exception sendError) {
                log.error("HIL 재개 에러 응답 전송 실패: {}", sendError.getMessage());
            }
        }
    }

    private Map<String, Object> processHilResumeRequest(QuviHilResumeDto request, WebSocketSession session) {
        log.info("🔄 WebSocket HIL 재개 요청 처리 시작: workflowId={}, userInput={}",
                request.getWorkflowId(), request.getUserInput());

        String workflowId = request.getWorkflowId();
        long startTime = System.currentTimeMillis();

        try {
            // 워크플로우 상태 확인
            if (!workflowService.isWorkflowWaiting(workflowId)) {
                throw new IllegalStateException("워크플로우가 대기 상태가 아닙니다: " + workflowId);
            }

            workflowService.resumeWorkflow(workflowId);

            // 프로파일링 시작
            requestProfiler.startRequest(workflowId);

            // 로그 컨텍스트 재개
            WorkflowLogContext logContext = chainLogManager.resumeWorkflowLog(workflowId);

            chainLogManager.addLog(workflowId, "RESUME_WEBSOCKET_HANDLER", LogLevel.INFO,
                    String.format("🔄 WebSocket HIL 워크플로우 재개 - userInput: %s", request.getUserInput()));

            // 워크플로우 타입 확인 및 재개
            String workflowType = workflowExecutionManagerService.determineWorkflowType(workflowId);

            workflowExecutionManagerService.resumeWorkflowAfterHil(workflowType, workflowId, request.getUserInput());

            // 최종 결과 조회
            Object finalState = workflowExecutionManagerService.getFinalStateForWorkflow(workflowType, workflowId);

            // Chain 완료
            String finalAnswer = workflowExecutionManagerService.extractFinalAnswer(workflowType, workflowId);
            workflowService.completeWorkflow(workflowId, finalAnswer);

            // 로그 컨텍스트 업데이트
            updateLogContextWithFinalState(logContext, workflowType, workflowId);

            // 응답 생성
            long totalTime = System.currentTimeMillis() - startTime;
            Map<String, Object> response = ResponseUtils.buildResponse(
                    workflowExecutionManagerService, request.getSessionId(), workflowId, new ArrayList<>(), totalTime, workflowType, requestProfiler, "WebSocket HIL 재개 성공");

            StatisticsUtils.logNodeExecutionStatistics(log, chainLogManager, workflowId, totalTime, requestProfiler.getProfile(workflowId), "RESUME_WEBSOCKET_STATISTICS");

            // 정리
            chainLogManager.completeWorkflow(workflowId, true);
            requestProfiler.clearProfile(workflowId);
            workflowExecutionManagerService.cleanupStateForWorkflow(workflowType, workflowId);

            log.info("WebSocket HIL 재개 처리 완료 - 소요시간: {}ms", totalTime);
            return response;

        } catch (Exception e) {
            log.error("❌ WebSocket HIL 재개 처리 중 예외 발생: {}", e.getMessage(), e);

            if (workflowId != null) {
                long totalTime = System.currentTimeMillis() - startTime;
                StatisticsUtils.logNodeExecutionStatistics(log, chainLogManager, workflowId, totalTime, requestProfiler.getProfile(workflowId), "RESUME_WEBSOCKET_STATISTICS");
                chainLogManager.completeWorkflow(workflowId, false);
                requestProfiler.clearProfile(workflowId);
                workflowExecutionManagerService.cleanupAllStates(workflowId);
            }

            return buildErrorResponse(e.getMessage());
        }
    }

    /**
     * 로그 컨텍스트에 최종 상태 업데이트
     */
    private void updateLogContextWithFinalState(WorkflowLogContext logContext, String selectedWorkflow, String workflowId) {
        try {
            String selectedTable = workflowExecutionManagerService.extractSelectedTable(selectedWorkflow, workflowId);
            String sqlQuery = workflowExecutionManagerService.extractSqlQuery(selectedWorkflow, workflowId);
            String finalAnswer = workflowExecutionManagerService.extractFinalAnswer(selectedWorkflow, workflowId);

            logContext.setSelectedTable(selectedTable);
            logContext.setSqlQuery(sqlQuery);
            logContext.setFinalAnswer(finalAnswer);

            if (!"JOY".equals(selectedWorkflow)) {
                UserInfo userInfo = workflowExecutionManagerService.extractUserInfo(selectedWorkflow, workflowId, null);
                logContext.setUserInfo(userInfo);
            } else {
                log.debug("JOY 워크플로우는 UserInfo를 로그 컨텍스트에 설정하지 않습니다.");
            }

        } catch (Exception e) {
            log.error("로그 컨텍스트 업데이트 실패 - selectedWorkflow: {}, workflowId: {}", selectedWorkflow, workflowId, e);
        }
    }

    /**
     * 오류 응답 생성
     */
    private Map<String, Object> buildErrorResponse(String errorMessage) {
        Map<String, Object> response = new HashMap<>();
        response.put("status", 500);
        response.put("success", false);
        response.put("retCd", 500);
        response.put("message", "WebSocket HIL 재개 실패");

        Map<String, Object> body = new HashMap<>();
        body.put("answer", "죄송합니다. HIL 재개 처리 중 오류가 발생했습니다.");
        body.put("error", errorMessage);

        response.put("body", body);
        return response;
    }
} 