package com.daquv.agent.quvi;

import com.daquv.agent.quvi.dto.QuviRequestDto;
import com.daquv.agent.quvi.llmadmin.WorkflowService;
import com.daquv.agent.quvi.llmadmin.SessionService;
import com.daquv.agent.quvi.logging.WorkflowLogContext;
import com.daquv.agent.quvi.logging.WorkflowLogManager;
import com.daquv.agent.quvi.dto.LogLevel;
import com.daquv.agent.quvi.requests.VectorRequest;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.workflow.WorkflowExecutionManagerService;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.List;
import java.util.Map;
import com.daquv.agent.quvi.util.StatisticsUtils;
import com.daquv.agent.quvi.util.ResponseUtils;

@Component
@Slf4j
public class ChatWebSocketHandler extends TextWebSocketHandler {

    private final VectorRequest vectorRequest;
    private final SessionService sessionService;
    private final WorkflowService workflowService;
    private final WorkflowLogManager chainLogManager;
    private final RequestProfiler requestProfiler;
    private final ObjectMapper objectMapper;

    @Autowired
    private WorkflowExecutionManagerService workflowExecutionManagerService;

    @Autowired
    private ChatController chatController;

    public ChatWebSocketHandler(VectorRequest vectorRequest, SessionService sessionService,
                                WorkflowService workflowService, WorkflowLogManager chainLogManager,
                                RequestProfiler requestProfiler, ObjectMapper objectMapper) {
        this.vectorRequest = vectorRequest;
        this.sessionService = sessionService;
        this.workflowService = workflowService;
        this.chainLogManager = chainLogManager;
        this.requestProfiler = requestProfiler;
        this.objectMapper = objectMapper;
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        try {
            String payload = message.getPayload();
            log.info("😊 WebSocket Chat 요청 수신: {}", payload);

            QuviRequestDto request = objectMapper.readValue(payload, QuviRequestDto.class);

            // WebSocket 처리 로직 실행 (세션 전달)
            Map<String, Object> response = processWebSocketRequest(request, session);

            // WebSocket으로 최종 응답 전송
            String responseJson = objectMapper.writeValueAsString(response);
            session.sendMessage(new TextMessage(responseJson));

            log.info("WebSocket 응답 전송 완료");

        } catch (Exception e) {
            log.error("❌ WebSocket 메시지 처리 중 예외 발생: {}", e.getMessage(), e);

            // 에러 응답 전송
            Map<String, Object> errorResponse = ResponseUtils.buildErrorResponse(e.getMessage(), "WebSocket Chat 실패");
            try {
                String errorJson = objectMapper.writeValueAsString(errorResponse);
                session.sendMessage(new TextMessage(errorJson));
            } catch (Exception sendError) {
                log.error("에러 응답 전송 실패: {}", sendError.getMessage());
            }
        }
    }

    private Map<String, Object> processWebSocketRequest(QuviRequestDto request, WebSocketSession session) {
        log.info("😊 WebSocket Chat 요청 처리 시작: {}", request);

        String workflowId = null;
        long startTime = System.currentTimeMillis();

        try {
            // 1. Session 처리
            String sessionId = sessionService.getOrCreateSessionId(request);
            log.info("💬 세션 ID: {}", sessionId);

            // 2. Workflow 생성
            workflowId = workflowService.createWorkflow(sessionId, request.getUserQuestion());
            log.info("🔗 체인 생성 완료: {}", workflowId);

            // 3. 프로파일링 시작
            requestProfiler.startRequest(workflowId);

            // 4. 로그 컨텍스트 생성
            WorkflowLogContext logContext = chainLogManager.createWorkflowLog(
                    workflowId,
                    request.getUserId(),
                    request.getUserQuestion()
            );
            logContext.setSessionId(sessionId);
            logContext.setCompanyId(request.getCompanyId());

            chainLogManager.addLog(workflowId, "CHAT_WEBSOCKET_HANDLER", LogLevel.INFO,
                    String.format("😊 WebSocket Chat 요청 수신 - userId: %s, question: %s",
                            request.getUserId(), request.getUserQuestion()));

            chainLogManager.addLog(workflowId, "CHAT_WEBSOCKET_HANDLER", LogLevel.INFO,
                    String.format("🔗 체인 생성 완료: %s, 세션 ID: %s", workflowId, sessionId));

            // 5. 추천 질문 검색
            List<String> recommendList = chatController.getRecommendations(request.getUserQuestion(), workflowId);

            // 6. SupervisorNode 실행하여 워크플로우 결정
            chainLogManager.addLog(workflowId, "CHAT_WEBSOCKET_HANDLER", LogLevel.INFO,
                    "🎯 Supervisor를 통한 워크플로우 선택 시작");

            String selectedWorkflow = chatController.selectWorkflowUsingSupervisor(request.getUserQuestion(), workflowId);

            if (selectedWorkflow == null || "ERROR".equals(selectedWorkflow)) {
                throw new RuntimeException("Supervisor에서 워크플로우 선택 실패");
            }

            chainLogManager.addLog(workflowId, "CHAT_WEBSOCKET_HANDLER", LogLevel.INFO,
                    String.format("🎯 선택된 워크플로우: %s", selectedWorkflow));

            // 7. 선택된 워크플로우에 따른 완전한 State 생성 및 초기화 (WebSocket 세션 포함)
            workflowExecutionManagerService.createAndInitializeStateForWorkflow(selectedWorkflow, request, sessionId, workflowId);

            // WebSocket 세션을 State에 설정
            setWebSocketSessionToState(selectedWorkflow, workflowId, session);

            chainLogManager.addLog(workflowId, "CHAT_WEBSOCKET_HANDLER", LogLevel.DEBUG,
                    "🔄 워크플로우 상태 초기화 완료");

            // 8. 워크플로우 실행
            chainLogManager.addLog(workflowId, "CHAT_WEBSOCKET_HANDLER", LogLevel.INFO,
                    "🚀 워크플로우 실행 시작");

            try {
                workflowExecutionManagerService.executeSelectedWorkflow(selectedWorkflow, workflowId);

                // HIL 상태 확인
                if (workflowExecutionManagerService.isWorkflowWaitingForHil(selectedWorkflow, workflowId)) {
                    log.info("WebSocket 워크플로우가 HIL 대기 상태입니다 - workflowId: {}", workflowId);
                    chainLogManager.addLog(workflowId, "CHAT_WEBSOCKET_HANDLER", LogLevel.INFO,
                            "⏸️ 워크플로우 HIL 대기 상태로 전환");

                    // HIL 응답 생성 및 반환
                    long totalTime = System.currentTimeMillis() - startTime;
                    Map<String, Object> hilResponse = ResponseUtils.buildHilWaitingResponse(
                            workflowExecutionManagerService, sessionId, workflowId, totalTime, selectedWorkflow, requestProfiler, "HIL 대기 중");

                    StatisticsUtils.logNodeExecutionStatistics(log, chainLogManager, workflowId, totalTime, requestProfiler.getProfile(workflowId), "CHAT_WEBSOCKET_STATISTICS");

                    // HIL 대기 상태에서는 정리하지 않고 상태 유지
                    log.info("HIL 대기 상태로 인해 WebSocket 상태를 유지합니다 - workflowId: {}", workflowId);
                    return hilResponse;
                } else {
                    chainLogManager.addLog(workflowId, "CHAT_WEBSOCKET_HANDLER", LogLevel.INFO, "✅ 워크플로우 실행 완료");
                }
            } catch (Exception workflowError) {
                chainLogManager.addLog(workflowId, "CHAT_WEBSOCKET_HANDLER", LogLevel.ERROR,
                        String.format("❌ 워크플로우 실행 실패: %s", removeHttpProtocol(workflowError.getMessage())), workflowError);

                StringWriter sw = new StringWriter();
                PrintWriter pw = new PrintWriter(sw);
                workflowError.printStackTrace(pw);
                chainLogManager.addLog(workflowId, "CHAT_WEBSOCKET_HANDLER", LogLevel.ERROR,
                        String.format("Stack Trace:\n%s", sw.toString()));

                throw workflowError;
            }

            // 10. Chain 완료
            String finalAnswer = workflowExecutionManagerService.extractFinalAnswer(selectedWorkflow, workflowId);
            workflowService.completeWorkflow(workflowId, finalAnswer);

            // 로그 컨텍스트에 최종 결과 저장
            chainLogManager.updateLogContextWithFinalState(logContext, selectedWorkflow, workflowId, request, workflowExecutionManagerService);

            // 11. 응답 생성
            long totalTime = System.currentTimeMillis() - startTime;
            Map<String, Object> response = ResponseUtils.buildResponse(
                    workflowExecutionManagerService, sessionId, workflowId, recommendList, totalTime, selectedWorkflow, requestProfiler, "WebSocket Chat 성공");

            StatisticsUtils.logNodeExecutionStatistics(log, chainLogManager, workflowId, totalTime, requestProfiler.getProfile(workflowId), "CHAT_WEBSOCKET_STATISTICS");

            // 12. 정리
            if (!workflowExecutionManagerService.isWorkflowWaitingForHil(selectedWorkflow, workflowId)) {
                chainLogManager.completeWorkflow(workflowId, true);
                requestProfiler.clearProfile(workflowId);
                workflowExecutionManagerService.cleanupStateForWorkflow(selectedWorkflow, workflowId);
            } else {
                // HIL 대기 상태인 경우는 정리하지 않고 상태 유지
                log.info("HIL 대기 상태로 인해 WebSocket 상태를 유지합니다 - workflowId: {}", workflowId);
            }

            log.info("WebSocket Chat 요청 처리 완료 - {}ms", totalTime);
            return response;

        } catch (Exception e) {
            log.error("❌ WebSocket Chat 요청 처리 실패", e);

            // 에러 발생시에도 통계 로깅
            if (workflowId != null) {
                long totalTime = System.currentTimeMillis() - startTime;
                StatisticsUtils.logNodeExecutionStatistics(log, chainLogManager, workflowId, totalTime, requestProfiler.getProfile(workflowId), "CHAT_WEBSOCKET_STATISTICS");
            }

            // 정리
            if (workflowId != null) {
                chainLogManager.completeWorkflow(workflowId, false);
                requestProfiler.clearProfile(workflowId);
                workflowExecutionManagerService.cleanupAllStates(workflowId);
            }

            return ResponseUtils.buildErrorResponse(e.getMessage(), "WebSocket Chat 실패");
        }
    }

    /**
     * WebSocket 세션을 각 워크플로우 State에 설정
     */
    private void setWebSocketSessionToState(String selectedWorkflow, String workflowId, WebSocketSession session) {
        try {
            Object state = workflowExecutionManagerService.getFinalStateForWorkflow(selectedWorkflow, workflowId);

            if ("DEFAULT".equals(selectedWorkflow)) {
                // DEFAULT 워크플로우는 WebSocket 세션을 지원하지 않음 (또는 필요 시 추가)
                log.debug("DEFAULT 워크플로우는 WebSocket 세션을 설정하지 않습니다.");
            } else if ("SEMANTICQUERY".equals(selectedWorkflow)) {
                if (state instanceof com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState) {
                    ((com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState) state).setWebSocketSession(session);
                    log.debug("SemanticQuery 워크플로우에 WebSocket 세션 설정 완료");
                }
            } else if ("TOOLUSE".equals(selectedWorkflow)) {
                if (state instanceof com.daquv.agent.workflow.tooluse.ToolUseWorkflowState) {
                    ((com.daquv.agent.workflow.tooluse.ToolUseWorkflowState) state).setWebSocketSession(session);
                    log.debug("ToolUse 워크플로우에 WebSocket 세션 설정 완료");
                }
            } else if ("JOY".equals(selectedWorkflow)) {
                // JOY 워크플로우는 State가 문자열이므로 WebSocket 세션 설정 불가
                log.debug("JOY 워크플로우는 WebSocket 세션을 설정하지 않습니다.");
            }
        } catch (Exception e) {
            log.warn("WebSocket 세션 설정 실패 - selectedWorkflow: {}, workflowId: {}", selectedWorkflow, workflowId, e);
        }
    }

    private String removeHttpProtocol(String text) {
        if (text == null) {
            return null;
        }

        // "java.lang" 을 "java_lang" 으로 치환
        return text.replaceAll("java\\.lang", "java_lang");
    }
} 