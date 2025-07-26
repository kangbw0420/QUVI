package com.daquv.agent.quvi;

import com.daquv.agent.quvi.dto.LogLevel;
import com.daquv.agent.quvi.dto.QuviRequestDto;
import com.daquv.agent.quvi.llmadmin.SessionService;
import com.daquv.agent.quvi.llmadmin.WorkflowService;
import com.daquv.agent.quvi.logging.WorkflowLogContext;
import com.daquv.agent.quvi.logging.WorkflowLogManager;
import com.daquv.agent.quvi.requests.VectorRequest;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.workflow.WorkflowExecutionManagerService;
import com.daquv.agent.workflow.SupervisorNode;
import com.daquv.agent.workflow.dto.UserInfo;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import javax.servlet.http.HttpServletRequest;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.*;
import com.daquv.agent.quvi.util.StatisticsUtils;
import com.daquv.agent.quvi.util.ResponseUtils;

@RestController
public class ChatController {

    private static final Logger log = LoggerFactory.getLogger(ChatController.class);

    private final VectorRequest vectorRequest;
    private final SessionService sessionService;
    private final WorkflowService workflowService;
    private final WorkflowLogManager chainLogManager;
    private final RequestProfiler requestProfiler;

    @Autowired
    private WorkflowExecutionManagerService workflowExecutionManagerService;

    @Autowired
    private ApplicationContext applicationContext;

    public ChatController(VectorRequest vectorRequest, SessionService sessionService,
                          WorkflowService workflowService, WorkflowLogManager chainLogManager,
                          RequestProfiler requestProfiler) {
        this.vectorRequest = vectorRequest;
        this.sessionService = sessionService;
        this.workflowService = workflowService;
        this.chainLogManager = chainLogManager;
        this.requestProfiler = requestProfiler;
    }

    @PostMapping("/chat")
    public ResponseEntity<Map<String, Object>> processInput(@RequestBody QuviRequestDto request,
                                                            HttpServletRequest httpRequest) {
        log.info("😊 HTTP Chat 요청 수신: {}", request);

        String workflowId = null;
        long startTime = System.currentTimeMillis();

        try {
            // 1. Session 처리
            String sessionId = sessionService.getOrCreateSessionId(request);
            log.info("💬 세션 ID: {}", sessionId);

            // 2. Workflow 생성
            workflowId = workflowService.createWorkflow(sessionId, request.getUserQuestion());
            log.info("🔗 체인 생성 완료: {}", workflowId);

            httpRequest.setAttribute("workflowId", workflowId);
            httpRequest.setAttribute("X-Workflow-Id", workflowId);
            log.info("Request Attribute에 workflowId 설정: {}", workflowId);

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

            chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.INFO,
                    String.format("😊 HTTP Chat 요청 수신 - userId: %s, question: %s",
                            request.getUserId(), request.getUserQuestion()));

            chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.INFO,
                    String.format("🔗 체인 생성 완료: %s, 세션 ID: %s", workflowId, sessionId));

            // 5. 추천 질문 검색
            List<String> recommendList = getRecommendations(request.getUserQuestion(), workflowId);

            // 6. SupervisorNode 실행하여 워크플로우 결정
            chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.INFO,
                    "🎯 Supervisor를 통한 워크플로우 선택 시작");

            String selectedWorkflow = selectWorkflowUsingSupervisor(request.getUserQuestion(), workflowId);

            if (selectedWorkflow == null || "ERROR".equals(selectedWorkflow)) {
                throw new RuntimeException("Supervisor에서 워크플로우 선택 실패");
            }

            chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.INFO,
                    String.format("🎯 선택된 워크플로우: %s", selectedWorkflow));

            // 7. 선택된 워크플로우에 따른 완전한 State 생성 및 초기화
            workflowExecutionManagerService.createAndInitializeStateForWorkflow(selectedWorkflow, request, sessionId, workflowId);

            chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.DEBUG,
                    "🔄 워크플로우 상태 초기화 완료");

            // 8. 워크플로우 실행
            chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.INFO,
                    "🚀 워크플로우 실행 시작");

            try {
                workflowExecutionManagerService.executeSelectedWorkflow(selectedWorkflow, workflowId);
                // HIL 상태 확인
                if (workflowExecutionManagerService.isWorkflowWaitingForHil(selectedWorkflow, workflowId)) {
                    log.info("워크플로우가 HIL 대기 상태입니다 - workflowId: {}", workflowId);
                    chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.INFO,
                            "⏸️ 워크플로우 HIL 대기 상태로 전환");

                    // HIL 응답 생성 및 반환 - 여기서 workflow_status: waiting 응답
                    long totalTime = System.currentTimeMillis() - startTime;
                    Map<String, Object> hilResponse = buildHilWaitingResponse(
                            sessionService.getOrCreateSessionId(request), workflowId, totalTime, selectedWorkflow);

                    StatisticsUtils.logNodeExecutionStatistics(log, chainLogManager, workflowId, totalTime, requestProfiler.getProfile(workflowId), "STATISTICS");

                    // HIL 대기 상태에서는 정리하지 않고 상태 유지
                    log.info("HIL 대기 상태로 인해 상태를 유지합니다 - workflowId: {}", workflowId);
                    return ResponseEntity.ok(hilResponse);
                } else {
                    chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.INFO, "✅ 워크플로우 실행 완료");
                }
            } catch (Exception workflowError) {
                chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.ERROR,
                        String.format("❌ 워크플로우 실행 실패: %s", removeHttpProtocol(workflowError.getMessage())), workflowError);

                StringWriter sw = new StringWriter();
                PrintWriter pw = new PrintWriter(sw);
                workflowError.printStackTrace(pw);
                chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.ERROR,
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
            Map<String, Object> response = ResponseUtils.buildResponse(
                    workflowExecutionManagerService, sessionId, workflowId, recommendList, totalTime, selectedWorkflow, requestProfiler, "질답 성공");

            StatisticsUtils.logNodeExecutionStatistics(log, chainLogManager, workflowId, totalTime, requestProfiler.getProfile(workflowId), "STATISTICS");

            // 12. 정리
            if (!workflowExecutionManagerService.isWorkflowWaitingForHil(selectedWorkflow, workflowId)) {
                chainLogManager.completeWorkflow(workflowId, true);
                requestProfiler.clearProfile(workflowId);
                workflowExecutionManagerService.cleanupStateForWorkflow(selectedWorkflow, workflowId);
            } else {
                // HIL 대기 상태인 경우는 정리하지 않고 상태 유지
                log.info("HIL 대기 상태로 인해 상태를 유지합니다 - workflowId: {}", workflowId);
            }

            log.info("HTTP Chat 요청 처리 완료 - 소요시간: {}ms", totalTime);
            return ResponseEntity.ok(response);

        } catch (Exception e) {
            log.error("❌ HTTP Chat 요청 처리 중 예외 발생: {}", e.getMessage(), e);

            // 에러 발생시에도 통계 로깅
            if (workflowId != null) {
                long totalTime = System.currentTimeMillis() - startTime;
                StatisticsUtils.logNodeExecutionStatistics(log, chainLogManager, workflowId, totalTime, requestProfiler.getProfile(workflowId), "STATISTICS");
            }

            // 정리
            if (workflowId != null) {
                chainLogManager.completeWorkflow(workflowId, false);
                requestProfiler.clearProfile(workflowId);
                workflowExecutionManagerService.cleanupAllStates(workflowId);
            }

            Map<String, Object> errorResponse = buildErrorResponse(e.getMessage());
            return ResponseEntity.ok(errorResponse);
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
            return "SuperVisor Node 실행 중 알 수 없는 오류";
        }
    }

    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("Chat Server is healthy! 🚀");
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

    /**
     * 추천 질문 검색
     */
    private List<String> getRecommendations(String userQuestion, String workflowId) {
        try {
            List<String> recommendList = vectorRequest.getRecommend(userQuestion, 4, workflowId);
            log.info("📚 추천 질문 검색 완료: {}", recommendList);
            chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.INFO,
                    String.format("📚 추천 질문 검색 완료: %d개", recommendList.size()));
            return recommendList;
        } catch (Exception e) {
            log.error("📚 추천 질문 검색 실패: {}", e.getMessage(), e);
            chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.ERROR,
                    "📚 벡터 스토어 연결 실패로 추천 질문을 가져올 수 없습니다");
            return new ArrayList<>();
        }
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

    /**
     * 오류 응답 생성
     */
    private Map<String, Object> buildErrorResponse(String errorMessage) {
        Map<String, Object> response = new HashMap<>();
        response.put("status", 500);
        response.put("success", false);
        response.put("retCd", 500);
        response.put("message", "질답 실패");

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
} 