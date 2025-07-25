package com.daquv.agent.quvi;

import com.daquv.agent.quvi.dto.LogLevel;
import com.daquv.agent.quvi.dto.QuviHilResumeDto;
import com.daquv.agent.quvi.dto.QuviRequestDto;
import com.daquv.agent.quvi.llmadmin.SessionService;
import com.daquv.agent.quvi.llmadmin.WorkflowService;
import com.daquv.agent.quvi.logging.ChainLogContext;
import com.daquv.agent.quvi.logging.ChainLogManager;
import com.daquv.agent.quvi.requests.VectorRequest;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.workflow.WorkflowExecutionManagerService;
import com.daquv.agent.workflow.ChainStateManager;
import com.daquv.agent.workflow.SupervisorNode;
import com.daquv.agent.workflow.WorkflowExecutionContext;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.workflow.dto.UserInfo;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState;
import com.daquv.agent.workflow.tooluse.ToolUseWorkflowState;
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

@RestController
public class QuviController {

    private static final Logger log = LoggerFactory.getLogger(QuviController.class);

    private final ChainStateManager stateManager;
    private final WorkflowExecutionContext workflowContext;
    private final VectorRequest vectorRequest;
    private final SessionService sessionService;
    private final WorkflowService workflowService;
    private final ChainLogManager chainLogManager;
    private final RequestProfiler requestProfiler;

    @Autowired
    private WorkflowExecutionManagerService workflowExecutionManagerService;

    @Autowired
    private ApplicationContext applicationContext;

    public QuviController(ChainStateManager stateManager, WorkflowExecutionContext workflowContext,
                          VectorRequest vectorRequest, SessionService sessionService,
                          WorkflowService workflowService, ChainLogManager chainLogManager,
                          RequestProfiler requestProfiler) {
        this.stateManager = stateManager;
        this.workflowContext = workflowContext;
        this.vectorRequest = vectorRequest;
        this.sessionService = sessionService;
        this.workflowService = workflowService;
        this.chainLogManager = chainLogManager;
        this.requestProfiler = requestProfiler;
    }

    @PostMapping("/process")
    public ResponseEntity<Map<String, Object>> processInput(@RequestBody QuviRequestDto request,
                                                            HttpServletRequest httpRequest) {
        log.info("😊 HTTP Quvi 요청 수신: {}", request);

        String workflowId = null;
        long startTime = System.currentTimeMillis();

        try {
            // 1. Session 처리
            String sessionId = getOrCreateSessionId(request);
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
            ChainLogContext logContext = chainLogManager.createChainLog(
                    workflowId,
                    request.getUserId(),
                    request.getUserQuestion()
            );
            logContext.setConversationId(sessionId);
            logContext.setCompanyId(request.getCompanyId());

            chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.INFO,
                    String.format("😊 HTTP Quvi 요청 수신 - userId: %s, question: %s",
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
                            getOrCreateSessionId(request), workflowId, totalTime, selectedWorkflow);

                    logNodeExecutionStatistics(workflowId, totalTime);

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
            Map<String, Object> response = buildResponse(sessionId, workflowId, recommendList, totalTime, selectedWorkflow);

            logNodeExecutionStatistics(workflowId, totalTime);

            // 12. 정리
            if (!workflowExecutionManagerService.isWorkflowWaitingForHil(selectedWorkflow, workflowId)) {
                chainLogManager.completeWorkflow(workflowId, true);
                requestProfiler.clearProfile(workflowId);
                workflowExecutionManagerService.cleanupStateForWorkflow(selectedWorkflow, workflowId);
            } else {
                // HIL 대기 상태인 경우는 정리하지 않고 상태 유지
                log.info("HIL 대기 상태로 인해 상태를 유지합니다 - workflowId: {}", workflowId);
            }

            log.info("HTTP Quvi 요청 처리 완료 - 소요시간: {}ms", totalTime);
            return ResponseEntity.ok(response);

        } catch (Exception e) {
            log.error("❌ HTTP Quvi 요청 처리 중 예외 발생: {}", e.getMessage(), e);

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

            Map<String, Object> errorResponse = buildErrorResponse(e.getMessage());
            return ResponseEntity.ok(errorResponse);
        }
    }

    /**
     * HIL 재개 처리를 위한 새로운 엔드포인트
     */
    @PostMapping("/resume")
    public ResponseEntity<Map<String, Object>> resumeWorkflow(@RequestBody QuviHilResumeDto request,
                                                              HttpServletRequest httpRequest) {
        log.info("🔄 HIL 워크플로우 재개 요청 수신: workflowId={}, userInput={}",
                request.getWorkflowId(), request.getUserInput());

        String workflowId = request.getWorkflowId();
        long startTime = System.currentTimeMillis();

        try {
            // 워크플로우 상태 확인
            if (!workflowService.isWorkflowWaiting(workflowId)) {
                throw new IllegalStateException("워크플로우가 대기 상태가 아닙니다: " + workflowId);
            }

            workflowService.resumeWorkflow(workflowId);

            httpRequest.setAttribute("workflowId", workflowId);
            httpRequest.setAttribute("X-Workflow-Id", workflowId);

            // 프로파일링 시작
            requestProfiler.startRequest(workflowId);

            // 로그 컨텍스트 재개
            ChainLogContext logContext = chainLogManager.resumeChainLog(workflowId);

            chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.INFO,
                    String.format("🔄 HIL 워크플로우 재개 - userInput: %s", request.getUserInput()));

            // 워크플로우 타입 확인 및 재개
            String workflowType = workflowExecutionManagerService.determineWorkflowType(workflowId);

            workflowExecutionManagerService.resumeWorkflowAfterHil(workflowType, workflowId, request.getUserInput());

            // 최종 결과 조회
            Object finalState = workflowExecutionManagerService.getFinalStateForWorkflow(workflowType, workflowId);

            // Chain 완료
            String finalAnswer = workflowExecutionManagerService.extractFinalAnswer(workflowType, workflowId);
            workflowService.completeWorkflow(workflowId, finalAnswer);

            // 로그 컨텍스트 업데이트
            updateLogContextWithFinalState(logContext, workflowType, workflowId, null);

            // 응답 생성
            long totalTime = System.currentTimeMillis() - startTime;
            Map<String, Object> response = buildResponse(
                    request.getSessionId(), workflowId, new ArrayList<>(), totalTime, workflowType);

            logNodeExecutionStatistics(workflowId, totalTime);

            // 정리
            chainLogManager.completeWorkflow(workflowId, true);
            requestProfiler.clearProfile(workflowId);
            workflowExecutionManagerService.cleanupStateForWorkflow(workflowType, workflowId);

            log.info("HIL 워크플로우 재개 처리 완료 - 소요시간: {}ms", totalTime);
            return ResponseEntity.ok(response);

        } catch (Exception e) {
            log.error("❌ HIL 워크플로우 재개 처리 중 예외 발생: {}", e.getMessage(), e);

            if (workflowId != null) {
                long totalTime = System.currentTimeMillis() - startTime;
                logNodeExecutionStatistics(workflowId, totalTime);
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
        return ResponseEntity.ok("Quvi Server is healthy! 🚀");
    }

    /**
     * 로그 컨텍스트에 최종 상태 업데이트
     */
    private void updateLogContextWithFinalState(ChainLogContext logContext, String selectedWorkflow, String workflowId, QuviRequestDto request) {
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
     * 세션 ID 확인 또는 새로 생성
     */
    private String getOrCreateSessionId(QuviRequestDto request) {
        String sessionId = request.getSessionId();

        if (sessionId != null && !sessionId.isEmpty() &&
                sessionService.checkConversationId(sessionId)) {

            log.debug("기존 세션 ID 사용: {}", sessionId);
            return sessionId;
        } else {
            String newSessionId = sessionService.makeSessionId(request.getUserId());

            log.debug("새 세션 ID 생성: {}", newSessionId);
            return newSessionId;
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
     * Executor 결과 처리 공통 로직
     */
    private void handleExecutorResults(WorkflowState state) {
        if (state.getSqlQuery() != null && !state.getSqlQuery().trim().isEmpty()) {
            if (state.getInvalidDate() != null && state.getInvalidDate()) {
                log.info("executor에서 invalid_date 감지 - 워크플로우 종료");
                return;
            }

            if (state.getNoData() != null && state.getNoData()) {
                workflowContext.executeNode("nodataNode", state);
                return;
            }

            if (state.getQueryError() != null && state.getQueryError() &&
                    (state.getSafeCount() == null || state.getSafeCount() < 2)) {
                workflowContext.executeNode("safeguardNode", state);

                if (state.getQueryChanged() != null && state.getQueryChanged()) {
                    workflowContext.executeNode("queryExecutorNode", state);

                    if (state.getInvalidDate() != null && state.getInvalidDate()) {
                        return;
                    }

                    if (state.getNoData() != null && state.getNoData()) {
                        workflowContext.executeNode("nodataNode", state);
                        return;
                    }
                }
            }

            if ("success".equals(state.getQueryResultStatus())) {
                workflowContext.executeNode("respondentNode", state);
            }
        } else {
            state.setQueryResultStatus("failed");
            state.setSqlError("SQL 쿼리가 생성되지 않았습니다.");
            log.error("SQL 쿼리 생성 실패");
        }
    }

    /**
     * 성공 응답 생성
     */
    private Map<String, Object> buildResponse(String conversationId, String chainId,
                                              List<String> recommendList, long totalTime,
                                              String selectedWorkflow) {
        Map<String, Object> response = new HashMap<>();

        // 기본 응답
        response.put("status", 200);
        response.put("success", true);
        response.put("retCd", 200);
        response.put("message", "질답 성공");

        // 응답 본문
        Map<String, Object> body = new HashMap<>();

        // 매니저를 통해 데이터 추출
        String finalAnswer = workflowExecutionManagerService.extractFinalAnswer(selectedWorkflow, chainId);
        if (finalAnswer == null || finalAnswer.trim().isEmpty()) {
            finalAnswer = "죄송합니다. 요청을 처리하는 중 오류가 발생했습니다.";
        }

        body.put("answer", finalAnswer);
        body.put("raw_data", workflowExecutionManagerService.extractQueryResult(selectedWorkflow, chainId));
        body.put("session_id", conversationId);
        body.put("chain_id", chainId);
        body.put("recommend", recommendList);
        body.put("is_api", false);
        body.put("date_info", Arrays.asList(
                workflowExecutionManagerService.extractStartDate(selectedWorkflow, chainId),
                workflowExecutionManagerService.extractEndDate(selectedWorkflow, chainId)
        ));
        body.put("sql_query", workflowExecutionManagerService.extractSqlQuery(selectedWorkflow, chainId));
        body.put("selected_table", workflowExecutionManagerService.extractSelectedTable(selectedWorkflow, chainId));
        body.put("has_next", workflowExecutionManagerService.extractHasNext(selectedWorkflow, chainId));
        body.put("workflow_status", "completed");
        body.put("hil_required", false);

        // 프로파일링 정보 (기존과 동일)
        Map<String, Object> profile = new HashMap<>();
        if (chainId != null) {
            Map<String, Object> profileData = requestProfiler.getProfile(chainId);

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
        } else {
            // 프로파일링이 비활성화된 경우 기본값 설정
            Map<String, Object> vectorDbDefault = new HashMap<>();
            vectorDbDefault.put("calls", 0);
            vectorDbDefault.put("total_time_ms", 0);
            vectorDbDefault.put("avg_time_ms", 0.0);
            profile.put("vector_db", vectorDbDefault);

            Map<String, Object> llmDefault = new HashMap<>();
            llmDefault.put("calls", 0);
            llmDefault.put("total_time_ms", 0);
            llmDefault.put("avg_time_ms", 0.0);
            profile.put("llm", llmDefault);

            Map<String, Object> dbNormalDefault = new HashMap<>();
            dbNormalDefault.put("calls", 0);
            dbNormalDefault.put("total_time_ms", 0);
            dbNormalDefault.put("avg_time_ms", 0.0);
            profile.put("db_normal", dbNormalDefault);

            Map<String, Object> dbPromptDefault = new HashMap<>();
            dbPromptDefault.put("calls", 0);
            dbPromptDefault.put("total_time_ms", 0);
            dbPromptDefault.put("avg_time_ms", 0.0);
            profile.put("db_prompt", dbPromptDefault);
        }
        profile.put("total_time_ms", totalTime);
        body.put("profile", profile);

        response.put("body", body);

        return response;
    }


    /**
     * HIL 대기 상태 응답 생성
     */
    private Map<String, Object> buildHilWaitingResponse(String conversationId, String chainId,
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
        String hilMessage = workflowExecutionManagerService.extractFinalAnswer(selectedWorkflow, chainId);

        if (hilMessage == null || hilMessage.trim().isEmpty()) {
            hilMessage = "추가 정보가 필요합니다. 사용자 입력을 기다리고 있습니다.";
        }

        body.put("answer", hilMessage);
        body.put("session_id", conversationId);
        body.put("workflow_id", chainId);
        body.put("workflow_status", "waiting");
        body.put("hil_required", true); // HIL이 필요함을 명시
        body.put("is_api", false);
        body.put("recommend", new ArrayList<>()); // HIL 상태에서는 추천 질문 없음

        // 프로파일링 정보 (기본값)
        Map<String, Object> profile = new HashMap<>();
        if (chainId != null) {
            Map<String, Object> profileData = requestProfiler.getProfile(chainId);

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

        log.info("HIL 대기 응답 생성 완료 - workflowId: {}, status: waiting", chainId);
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

    /**
     * 각 노드별 실행 통계 로깅 (워크플로우 노드별)
     */
    private void logNodeExecutionStatistics(String workflowId, long totalTime) {
        try {
            Map<String, Object> profileData = requestProfiler.getProfile(workflowId);

            log.info("📊 ===== 워크플로우 노드별 실행 통계 (Chain ID: {}) =====", workflowId);
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
                log.info("📊 ===== 워크플로우 노드별 세분화 통계 =====");

                for (Map.Entry<String, Object> nodeEntry : workflowNodes.entrySet()) {
                    String nodeId = nodeEntry.getKey();
                    Map<String, Object> nodeData = (Map<String, Object>) nodeEntry.getValue();

                    int totalCalls = (Integer) nodeData.getOrDefault("total_calls", 0);
                    long totalTimeMs = (Long) nodeData.getOrDefault("total_time_ms", 0L);
                    double avgTime = (Double) nodeData.getOrDefault("avg_time_ms", 0.0);

                    log.info("📊 🔧 {} 노드 - 총 호출: {}회, 총 시간: {}ms, 평균: {}ms",
                            nodeId, totalCalls, totalTimeMs, avgTime);

                    chainLogManager.addLog(workflowId, "STATISTICS", LogLevel.INFO,
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

                            chainLogManager.addLog(workflowId, "STATISTICS", LogLevel.INFO,
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

            log.info("📊 ⭐ 전체 요약 - 총 노드 호출: {}회, 프로파일된 시간: {}ms ({}%), 기타 처리 시간: {}ms",
                    totalCalls, totalProfiledTime, profiledPercentage, totalTime - totalProfiledTime);

            chainLogManager.addLog(workflowId, "STATISTICS", LogLevel.INFO,
                    String.format("⭐ 전체 요약 - 총 노드 호출: %d회, 프로파일된 시간: %dms (%.1f%%), 기타 처리 시간: %dms",
                            totalCalls, totalProfiledTime, profiledPercentage, totalTime - totalProfiledTime));

            log.info("📊 ===== 통계 종료 =====");

        } catch (Exception e) {
            log.warn("📊 워크플로우 노드별 실행 통계 로깅 중 오류 발생: {}", e.getMessage(), e);
        }
    }
}