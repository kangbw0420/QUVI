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
import com.daquv.agent.workflow.SupervisorNode;
import com.daquv.agent.workflow.dto.UserInfo;
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
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Component
@Slf4j
public class QuviWebSocketHandler extends TextWebSocketHandler {

    private final VectorRequest vectorRequest;
    private final SessionService sessionService;
    private final WorkflowService workflowService;
    private final WorkflowLogManager chainLogManager;
    private final RequestProfiler requestProfiler;
    private final ObjectMapper objectMapper;

    @Autowired
    private WorkflowExecutionManagerService workflowExecutionManagerService;

    @Autowired
    private ApplicationContext applicationContext;

    public QuviWebSocketHandler(VectorRequest vectorRequest, SessionService sessionService,
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
            log.info("😊 WebSocket Quvi 요청 수신: {}", payload);

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
            Map<String, Object> errorResponse = buildErrorResponse(e.getMessage());
            try {
                String errorJson = objectMapper.writeValueAsString(errorResponse);
                session.sendMessage(new TextMessage(errorJson));
            } catch (Exception sendError) {
                log.error("에러 응답 전송 실패: {}", sendError.getMessage());
            }
        }
    }

    private Map<String, Object> processWebSocketRequest(QuviRequestDto request, WebSocketSession session) {
        log.info("😊 WebSocket Quvi 요청 처리 시작: {}", request);

        String workflowId = null;
        long startTime = System.currentTimeMillis();

        try {
            // 1. Session 처리
            String sessionId = getOrCreateSessionId(request);
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

            chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.INFO,
                    String.format("😊 WebSocket Quvi 요청 수신 - userId: %s, question: %s",
                            request.getUserId(), request.getUserQuestion()));

            chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.INFO,
                    String.format("🔗 체인 생성 완료: %s, 세션 ID: %s", workflowId, sessionId));

            // 5. 추천 질문 검색
            List<String> recommendList = getRecommendations(request.getUserQuestion(), workflowId);

            // 6. SupervisorNode 실행하여 워크플로우 결정
            chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.INFO,
                    "🎯 Supervisor를 통한 워크플로우 선택 시작");

            String selectedWorkflow = selectWorkflowUsingSupervisor(request.getUserQuestion(), workflowId);

            if (selectedWorkflow == null || "ERROR".equals(selectedWorkflow)) {
                throw new RuntimeException("Supervisor에서 워크플로우 선택 실패");
            }

            chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.INFO,
                    String.format("🎯 선택된 워크플로우: %s", selectedWorkflow));

            // 7. 선택된 워크플로우에 따른 완전한 State 생성 및 초기화 (WebSocket 세션 포함)
            workflowExecutionManagerService.createAndInitializeStateForWorkflow(selectedWorkflow, request, sessionId, workflowId);

            // WebSocket 세션을 State에 설정
            setWebSocketSessionToState(selectedWorkflow, workflowId, session);

            chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.DEBUG,
                    "🔄 워크플로우 상태 초기화 완료");

            // 8. 워크플로우 실행
            chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.INFO,
                    "🚀 워크플로우 실행 시작");

            try {
                workflowExecutionManagerService.executeSelectedWorkflow(selectedWorkflow, workflowId);

                // HIL 상태 확인
                if (workflowExecutionManagerService.isWorkflowWaitingForHil(selectedWorkflow, workflowId)) {
                    log.info("WebSocket 워크플로우가 HIL 대기 상태입니다 - workflowId: {}", workflowId);
                    chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.INFO,
                            "⏸️ 워크플로우 HIL 대기 상태로 전환");

                    // HIL 응답 생성 및 반환
                    long totalTime = System.currentTimeMillis() - startTime;
                    Map<String, Object> hilResponse = buildHilWaitingResponse(
                            sessionId, workflowId, totalTime, selectedWorkflow);

                    logNodeExecutionStatistics(workflowId, totalTime);

                    // HIL 대기 상태에서는 정리하지 않고 상태 유지
                    log.info("HIL 대기 상태로 인해 WebSocket 상태를 유지합니다 - workflowId: {}", workflowId);
                    return hilResponse;
                } else {
                    chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.INFO, "✅ 워크플로우 실행 완료");
                }
            } catch (Exception workflowError) {
                chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.ERROR,
                        String.format("❌ 워크플로우 실행 실패: %s", removeHttpProtocol(workflowError.getMessage())), workflowError);

                StringWriter sw = new StringWriter();
                PrintWriter pw = new PrintWriter(sw);
                workflowError.printStackTrace(pw);
                chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.ERROR,
                        String.format("Stack Trace:\n%s", sw.toString()));

                throw workflowError;
            }

            // 9. 최종 결과 조회
            Object finalState = workflowExecutionManagerService.getFinalStateForWorkflow(selectedWorkflow, workflowId);

            // 10. Chain 완료
            String finalAnswer = workflowExecutionManagerService.extractFinalAnswer(selectedWorkflow, workflowId);
            workflowService.completeWorkflow(workflowId, finalAnswer);

            // 로그 컨텍스트에 최종 결과 저장
            updateLogContextWithFinalState(logContext, selectedWorkflow, workflowId, request);

            // 11. 응답 생성
            long totalTime = System.currentTimeMillis() - startTime;
            Map<String, Object> response = buildResponse(sessionId, workflowId, recommendList, totalTime, selectedWorkflow);

            logNodeExecutionStatistics(workflowId, totalTime);

            // 12. 정리
            if (!workflowExecutionManagerService.isWorkflowWaitingForHil(selectedWorkflow, workflowId)) {
                chainLogManager.completeWorkflow(workflowId, true);
                requestProfiler.clearProfile(workflowId);
                workflowExecutionManagerService.cleanupStateForWorkflow(selectedWorkflow, workflowId);
            } else {
                // HIL 대기 상태인 경우는 정리하지 않고 상태 유지
                log.info("HIL 대기 상태로 인해 WebSocket 상태를 유지합니다 - workflowId: {}", workflowId);
            }

            log.info("WebSocket 요청 처리 완료 - {}ms", totalTime);
            return response;

        } catch (Exception e) {
            log.error("❌ WebSocket 요청 처리 실패", e);

            // 에러 발생시에도 통계 로깅
            if (workflowId != null) {
                long totalTime = System.currentTimeMillis() - startTime;
                logNodeExecutionStatistics(workflowId, totalTime);
            }

            // 정리
            if (workflowId != null) {
                chainLogManager.completeWorkflow(workflowId, false);
                requestProfiler.clearProfile(workflowId);
                workflowExecutionManagerService.cleanupAllStates(workflowId);
            }

            return buildErrorResponse(e.getMessage());
        }
    }

    private String selectWorkflowUsingSupervisor(String userQuestion, String workflowId) {
        try {
            Object supervisorNodeBean = applicationContext.getBean("supervisorNode");

            if (supervisorNodeBean instanceof SupervisorNode) {
                SupervisorNode supervisorNode = (SupervisorNode) supervisorNodeBean;

                log.info("🎯 SupervisorNode 실행 시작 - 질문: {}", userQuestion);

                // userQuestion만으로 워크플로우 선택 실행
                String selectedWorkflow = supervisorNode.selectWorkflow(userQuestion, workflowId);

                log.info("🎯 SupervisorNode 실행 완료 - 선택된 워크플로우: {}", selectedWorkflow);
                return selectedWorkflow;

            } else {
                throw new IllegalArgumentException("SupervisorNode를 찾을 수 없습니다.");
            }

        } catch (Exception e) {
            log.error("SupervisorNode 실행 실패: {}", e.getMessage(), e);
            return "ERROR";
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

    private String getOrCreateSessionId(QuviRequestDto request) {
        String sessionId = request.getSessionId();

        if (sessionId != null && !sessionId.isEmpty() &&
                sessionService.checkSessionId(sessionId)) {

            log.debug("기존 세션 ID 사용: {}", sessionId);
            return sessionId;
        } else {
            String newSessionId = sessionService.makeSessionId(request.getUserId());
            log.debug("새 세션 ID 생성: {}", newSessionId);
            return newSessionId;
        }
    }

    private List<String> getRecommendations(String userQuestion, String workflowId) {
        try {
            List<String> recommendList = vectorRequest.getRecommend(userQuestion, 4, workflowId);
            log.info("📚 추천 질문 검색 완료: {}", recommendList);
            chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.INFO,
                    String.format("📚 추천 질문 검색 완료: %d개", recommendList.size()));
            return recommendList;
        } catch (Exception e) {
            log.error("📚 추천 질문 검색 실패: {}", e.getMessage(), e);
            chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.ERROR,
                    "📚 벡터 스토어 연결 실패로 추천 질문을 가져올 수 없습니다");
            return new ArrayList<>();
        }
    }

    /**
     * 로그 컨텍스트에 최종 상태 업데이트
     */
    private void updateLogContextWithFinalState(WorkflowLogContext logContext, String selectedWorkflow, String workflowId, QuviRequestDto request) {
        try {
            String selectedTable = workflowExecutionManagerService.extractSelectedTable(selectedWorkflow, workflowId);
            String sqlQuery = workflowExecutionManagerService.extractSqlQuery(selectedWorkflow, workflowId);
            String finalAnswer = workflowExecutionManagerService.extractFinalAnswer(selectedWorkflow, workflowId);

            logContext.setSelectedTable(selectedTable);
            logContext.setSqlQuery(sqlQuery);
            logContext.setFinalAnswer(finalAnswer);

            if (!"JOY".equals(selectedWorkflow)) {
                UserInfo userInfo = workflowExecutionManagerService.extractUserInfo(selectedWorkflow, workflowId, request);
                logContext.setUserInfo(userInfo);
            } else {
                log.debug("JOY 워크플로우는 UserInfo를 로그 컨텍스트에 설정하지 않습니다.");
            }

        } catch (Exception e) {
            log.error("로그 컨텍스트 업데이트 실패 - selectedWorkflow: {}, workflowId: {}", selectedWorkflow, workflowId, e);
        }
    }

    private Map<String, Object> buildResponse(String sessionId, String workflowId,
                                              List<String> recommendList, long totalTime,
                                              String selectedWorkflow) {
        Map<String, Object> response = new HashMap<>();

        // 기본 응답
        response.put("status", 200);
        response.put("success", true);
        response.put("retCd", 200);
        response.put("message", "WebSocket 질답 성공");

        // 응답 본문
        Map<String, Object> body = new HashMap<>();

        // 매니저를 통해 데이터 추출
        String finalAnswer = workflowExecutionManagerService.extractFinalAnswer(selectedWorkflow, workflowId);
        if (finalAnswer == null || finalAnswer.trim().isEmpty()) {
            finalAnswer = "죄송합니다. 요청을 처리하는 중 오류가 발생했습니다.";
        }

        body.put("answer", finalAnswer);
        body.put("raw_data", workflowExecutionManagerService.extractQueryResult(selectedWorkflow, workflowId));
        body.put("session_id", sessionId);
        body.put("workflow_id", workflowId);
        body.put("recommend", recommendList);
        body.put("is_api", false);
        body.put("date_info", Arrays.asList(
                workflowExecutionManagerService.extractStartDate(selectedWorkflow, workflowId),
                workflowExecutionManagerService.extractEndDate(selectedWorkflow, workflowId)
        ));
        body.put("sql_query", workflowExecutionManagerService.extractSqlQuery(selectedWorkflow, workflowId));
        body.put("selected_table", workflowExecutionManagerService.extractSelectedTable(selectedWorkflow, workflowId));
        body.put("has_next", workflowExecutionManagerService.extractHasNext(selectedWorkflow, workflowId));
        body.put("workflow_status", "completed");
        body.put("hil_required", false);

        // 프로파일링 정보
        Map<String, Object> profile = new HashMap<>();
        if (workflowId != null) {
            Map<String, Object> profileData = requestProfiler.getProfile(workflowId);

            // vector_db
            Map<String, Object> vectorDbDefault = new HashMap<>();
            vectorDbDefault.put("calls", 0);
            vectorDbDefault.put("total_time_ms", 0);
            vectorDbDefault.put("avg_time_ms", 0.0);
            profile.put("vector_db", profileData.getOrDefault("vector_db", vectorDbDefault));

            // llm
            Map<String, Object> llmDefault = new HashMap<>();
            llmDefault.put("calls", 0);
            llmDefault.put("total_time_ms", 0);
            llmDefault.put("avg_time_ms", 0.0);
            profile.put("llm", profileData.getOrDefault("llm", llmDefault));

            // db_normal (기존 db_main)
            Map<String, Object> dbNormalDefault = new HashMap<>();
            dbNormalDefault.put("calls", 0);
            dbNormalDefault.put("total_time_ms", 0);
            dbNormalDefault.put("avg_time_ms", 0.0);
            profile.put("db_normal", profileData.getOrDefault("db_main", dbNormalDefault));

            // db_prompt
            Map<String, Object> dbPromptDefault = new HashMap<>();
            dbPromptDefault.put("calls", 0);
            dbPromptDefault.put("total_time_ms", 0);
            dbPromptDefault.put("avg_time_ms", 0.0);
            profile.put("db_prompt", profileData.getOrDefault("db_prompt", dbPromptDefault));
        }
        profile.put("total_time_ms", totalTime);
        body.put("profile", profile);

        response.put("body", body);
        return response;
    }

    /**
     * HIL 대기 상태 응답 생성
     */
    private Map<String, Object> buildHilWaitingResponse(String sessionId, String workflowId,
                                                        long totalTime, String selectedWorkflow) {
        Map<String, Object> response = new HashMap<>();

        // 기본 응답
        response.put("status", 200);
        response.put("success", true);
        response.put("retCd", 200);
        response.put("message", "HIL 대기 중");

        // 응답 본문
        Map<String, Object> body = new HashMap<>();

        // HIL 상태에서 필요한 정보들 (매니저를 통해 추출)
        String hilMessage = workflowExecutionManagerService.extractFinalAnswer(selectedWorkflow, workflowId);

        if (hilMessage == null || hilMessage.trim().isEmpty()) {
            hilMessage = "추가 정보가 필요합니다. 사용자 입력을 기다리고 있습니다.";
        }

        body.put("answer", hilMessage);
        body.put("session_id", sessionId);
        body.put("workflow_id", workflowId);
        body.put("workflow_status", "waiting");
        body.put("hil_required", true); // HIL이 필요함을 명시
        body.put("is_api", false);
        body.put("recommend", new ArrayList<>()); // HIL 상태에서는 추천 질문 없음

        // 프로파일링 정보 (기본값)
        Map<String, Object> profile = new HashMap<>();
        if (workflowId != null) {
            Map<String, Object> profileData = requestProfiler.getProfile(workflowId);

            // 기본 프로파일 구조 유지
            Map<String, Object> vectorDbDefault = new HashMap<>();
            vectorDbDefault.put("calls", 0);
            vectorDbDefault.put("total_time_ms", 0);
            vectorDbDefault.put("avg_time_ms", 0.0);
            profile.put("vector_db", profileData.getOrDefault("vector_db", vectorDbDefault));

            Map<String, Object> llmDefault = new HashMap<>();
            llmDefault.put("calls", 0);
            llmDefault.put("total_time_ms", 0);
            llmDefault.put("avg_time_ms", 0.0);
            profile.put("llm", profileData.getOrDefault("llm", llmDefault));

            Map<String, Object> dbNormalDefault = new HashMap<>();
            dbNormalDefault.put("calls", 0);
            dbNormalDefault.put("total_time_ms", 0);
            dbNormalDefault.put("avg_time_ms", 0.0);
            profile.put("db_normal", profileData.getOrDefault("db_main", dbNormalDefault));

            Map<String, Object> dbPromptDefault = new HashMap<>();
            dbPromptDefault.put("calls", 0);
            dbPromptDefault.put("total_time_ms", 0);
            dbPromptDefault.put("avg_time_ms", 0.0);
            profile.put("db_prompt", profileData.getOrDefault("db_prompt", dbPromptDefault));
        }
        profile.put("total_time_ms", totalTime);
        body.put("profile", profile);

        response.put("body", body);

        log.info("HIL 대기 응답 생성 완료 - workflowId: {}, status: waiting", workflowId);
        return response;
    }

    private Map<String, Object> buildErrorResponse(String errorMessage) {
        Map<String, Object> response = new HashMap<>();
        response.put("status", 500);
        response.put("success", false);
        response.put("retCd", 500);
        response.put("message", "WebSocket 질답 실패");

        Map<String, Object> body = new HashMap<>();
        body.put("answer", "죄송합니다. 요청을 처리하는 중 오류가 발생했습니다.");
        body.put("error", errorMessage);

        response.put("body", body);
        return response;
    }

    private String removeHttpProtocol(String text) {
        if (text == null) {
            return null;
        }

        // "java.lang" 을 "java_lang" 으로 치환
        return text.replaceAll("java\\.lang", "java_lang");
    }

    /**
     * 타입별 아이콘 반환
     */
    private String getTypeIcon(String type) {
        switch (type) {
            case "vector_db":
                return "🔍";
            case "llm":
                return "🤖";
            case "db_main":
                return "🗄️";
            case "db_prompt":
                return "💾";
            default:
                return "❓";
        }
    }

    /**
     * 각 노드별 실행 통계 로깅 (워크플로우 노드별)
     */
    private void logNodeExecutionStatistics(String workflowId, long totalTime) {
        try {
            Map<String, Object> profileData = requestProfiler.getProfile(workflowId);

            log.info("📊 ===== WebSocket 워크플로우 노드별 실행 통계 (Chain ID: {}) =====", workflowId);
            log.info("📊 전체 처리 시간: {}ms", totalTime);

            // 전체 타입별 요약 통계
            Map<String, Object> vectorDbStats = (Map<String, Object>) profileData.get("vector_db");
            Map<String, Object> llmStats = (Map<String, Object>) profileData.get("llm");
            Map<String, Object> dbMainStats = (Map<String, Object>) profileData.get("db_main");
            Map<String, Object> dbPromptStats = (Map<String, Object>) profileData.get("db_prompt");

            if (vectorDbStats != null) {
                int vectorCalls = (Integer) vectorDbStats.getOrDefault("calls", 0);
                long vectorTotalTime = (Long) vectorDbStats.getOrDefault("total_time_ms", 0L);
                double vectorAvgTime = (Double) vectorDbStats.getOrDefault("avg_time_ms", 0.0);

                log.info("📊 🔍 Vector DB 전체 - 호출횟수: {}회, 총 소요시간: {}ms, 평균 소요시간: {}ms",
                        vectorCalls, vectorTotalTime, vectorAvgTime);
            }

            if (llmStats != null) {
                int llmCalls = (Integer) llmStats.getOrDefault("calls", 0);
                long llmTotalTime = (Long) llmStats.getOrDefault("total_time_ms", 0L);
                double llmAvgTime = (Double) llmStats.getOrDefault("avg_time_ms", 0.0);

                log.info("📊 🤖 LLM 전체 - 호출횟수: {}회, 총 소요시간: {}ms, 평균 소요시간: {}ms",
                        llmCalls, llmTotalTime, llmAvgTime);
            }

            if (dbMainStats != null) {
                int dbMainCalls = (Integer) dbMainStats.getOrDefault("calls", 0);
                long dbMainTotalTime = (Long) dbMainStats.getOrDefault("total_time_ms", 0L);
                double dbMainAvgTime = (Double) dbMainStats.getOrDefault("avg_time_ms", 0.0);

                log.info("📊 🗄️ DB Main 전체 - 호출횟수: {}회, 총 소요시간: {}ms, 평균 소요시간: {}ms",
                        dbMainCalls, dbMainTotalTime, dbMainAvgTime);
            }

            if (dbPromptStats != null) {
                int dbPromptCalls = (Integer) dbPromptStats.getOrDefault("calls", 0);
                long dbPromptTotalTime = (Long) dbPromptStats.getOrDefault("total_time_ms", 0L);
                double dbPromptAvgTime = (Double) dbPromptStats.getOrDefault("avg_time_ms", 0.0);

                log.info("📊 💾 DB Prompt 전체 - 호출횟수: {}회, 총 소요시간: {}ms, 평균 소요시간: {}ms",
                        dbPromptCalls, dbPromptTotalTime, dbPromptAvgTime);
            }

            // 워크플로우 노드별 세분화된 통계
            Map<String, Object> workflowNodes = (Map<String, Object>) profileData.get("workflow_nodes");
            if (workflowNodes != null && !workflowNodes.isEmpty()) {
                log.info("📊 ===== WebSocket 워크플로우 노드별 세분화 통계 =====");

                for (Map.Entry<String, Object> nodeEntry : workflowNodes.entrySet()) {
                    String nodeId = nodeEntry.getKey();
                    Map<String, Object> nodeData = (Map<String, Object>) nodeEntry.getValue();

                    int totalCalls = (Integer) nodeData.getOrDefault("total_calls", 0);
                    long totalTimeMs = (Long) nodeData.getOrDefault("total_time_ms", 0L);
                    double avgTime = (Double) nodeData.getOrDefault("avg_time_ms", 0.0);

                    log.info("📊 🔧 {} 노드 - 총 호출: {}회, 총 시간: {}ms, 평균: {}ms",
                            nodeId, totalCalls, totalTimeMs, avgTime);

                    chainLogManager.addLog(workflowId, "WEBSOCKET_STATISTICS", LogLevel.INFO,
                            String.format("🔧 %s 노드 - 총 호출: %d회, 총 시간: %dms, 평균: %.2fms",
                                    nodeId, totalCalls, totalTimeMs, avgTime));

                    // 각 노드의 세부 타입별 통계
                    Map<String, Object> details = (Map<String, Object>) nodeData.get("details");
                    if (details != null && !details.isEmpty()) {
                        for (Map.Entry<String, Object> detailEntry : details.entrySet()) {
                            String type = detailEntry.getKey();
                            Map<String, Object> typeStats = (Map<String, Object>) detailEntry.getValue();

                            int typeCalls = (Integer) typeStats.getOrDefault("calls", 0);
                            long typeTime = (Long) typeStats.getOrDefault("total_time_ms", 0L);
                            double typeAvg = (Double) typeStats.getOrDefault("avg_time_ms", 0.0);

                            String typeIcon = getTypeIcon(type);
                            log.info("📊   └─ {} {}: {}회, {}ms, 평균 {}ms",
                                    typeIcon, type, typeCalls, typeTime, typeAvg);

                            chainLogManager.addLog(workflowId, "WEBSOCKET_STATISTICS", LogLevel.INFO,
                                    String.format("    └─ %s %s: %d회, %dms, 평균 %.2fms",
                                            typeIcon, type, typeCalls, typeTime, typeAvg));
                        }
                    }
                }
            }

            // 전체 요약
            int totalCalls = 0;
            long totalProfiledTime = 0L;

            if (vectorDbStats != null) {
                totalCalls += (Integer) vectorDbStats.getOrDefault("calls", 0);
                totalProfiledTime += (Long) vectorDbStats.getOrDefault("total_time_ms", 0L);
            }
            if (llmStats != null) {
                totalCalls += (Integer) llmStats.getOrDefault("calls", 0);
                totalProfiledTime += (Long) llmStats.getOrDefault("total_time_ms", 0L);
            }
            if (dbMainStats != null) {
                totalCalls += (Integer) dbMainStats.getOrDefault("calls", 0);
                totalProfiledTime += (Long) dbMainStats.getOrDefault("total_time_ms", 0L);
            }
            if (dbPromptStats != null) {
                totalCalls += (Integer) dbPromptStats.getOrDefault("calls", 0);
                totalProfiledTime += (Long) dbPromptStats.getOrDefault("total_time_ms", 0L);
            }

            double profiledPercentage = totalTime > 0 ? (double) totalProfiledTime / totalTime * 100 : 0.0;

            log.info("📊 ⭐ WebSocket 전체 요약 - 총 노드 호출: {}회, 프로파일된 시간: {}ms ({}%), 기타 처리 시간: {}ms",
                    totalCalls, totalProfiledTime, profiledPercentage, totalTime - totalProfiledTime);

            chainLogManager.addLog(workflowId, "WEBSOCKET_STATISTICS", LogLevel.INFO,
                    String.format("⭐ WebSocket 전체 요약 - 총 노드 호출: %d회, 프로파일된 시간: %dms (%.1f%%), 기타 처리 시간: %dms",
                            totalCalls, totalProfiledTime, profiledPercentage, totalTime - totalProfiledTime));

            log.info("📊 ===== WebSocket 통계 종료 =====");

        } catch (Exception e) {
            log.warn("📊 WebSocket 워크플로우 노드별 실행 통계 로깅 중 오류 발생: {}", e.getMessage(), e);
        }
    }
}