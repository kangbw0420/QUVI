package com.daquv.agent.quvi;

import com.daquv.agent.quvi.dto.LogLevel;
import com.daquv.agent.quvi.dto.QuviRequestDto;
import com.daquv.agent.quvi.llmadmin.WorkflowService;
import com.daquv.agent.quvi.llmadmin.SessionService;
import com.daquv.agent.quvi.logging.ChainLogContext;
import com.daquv.agent.quvi.logging.ChainLogManager;
import com.daquv.agent.quvi.requests.VectorRequest;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.workflow.ChainStateManager;
import com.daquv.agent.workflow.WorkflowExecutionContext;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.workflow.dto.UserInfo;
import com.daquv.agent.workflow.SupervisorNode;
import com.daquv.agent.workflow.killjoy.KilljoyWorkflowExecutionContext;
import com.daquv.agent.workflow.semanticquery.SemanticQueryStateManager;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowExecutionContext;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState;
import com.daquv.agent.workflow.tooluse.ToolUseStateManager;
import com.daquv.agent.workflow.tooluse.ToolUseWorkflowExecutionContext;
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
    private KilljoyWorkflowExecutionContext killjoyWorkflowExecutionContext;

    @Autowired
    private ApplicationContext applicationContext;

    @Autowired
    private ToolUseWorkflowExecutionContext toolUseWorkflowContext;

    @Autowired
    private ToolUseStateManager toolUseStateManager;

    @Autowired
    private SemanticQueryWorkflowExecutionContext semanticQueryWorkflowContext;

    @Autowired
    private SemanticQueryStateManager semanticQueryStateManager;

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
            Object finalState = createAndInitializeStateForWorkflow(selectedWorkflow, request, sessionId, workflowId);

            chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.DEBUG,
                    "🔄 워크플로우 상태 초기화 완료");

            // 8. 워크플로우 실행
            chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.INFO,
                    "🚀 워크플로우 실행 시작");

            try {
                executeSelectedWorkflow(selectedWorkflow, workflowId);
                chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.INFO, "✅ 워크플로우 실행 완료");
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

            // 8. 최종 결과 조회
            Object retrievedFinalState = getFinalStateForWorkflow(selectedWorkflow, workflowId);

            // 9. Chain 완료
            String finalAnswer = extractFinalAnswer(retrievedFinalState);
            workflowService.completeWorkflow(workflowId, finalAnswer);

            // 로그 컨텍스트에 최종 결과 저장
            updateLogContextWithFinalState(logContext, retrievedFinalState);

            // 10. 응답 생성
            long totalTime = System.currentTimeMillis() - startTime;
            Map<String, Object> response = buildResponse(sessionId, workflowId, recommendList, totalTime, retrievedFinalState);

            logNodeExecutionStatistics(workflowId, totalTime);

            // 11. 정리
            chainLogManager.completeWorkflow(workflowId, true);
            requestProfiler.clearProfile(workflowId);
            cleanupStateForWorkflow(selectedWorkflow, workflowId);

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
                cleanupAllStates(workflowId);
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
            return "DEFAULT"; // 에러 시 기본 워크플로우로 폴백
        }
    }

    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("Quvi Server is healthy! 🚀");
    }

    /**
     * 워크플로우에 따른 적절한 State 생성 및 초기화
     */
    private Object createAndInitializeStateForWorkflow(String selectedWorkflow, QuviRequestDto request,
                                                       String sessionId, String workflowId) {
        switch (selectedWorkflow) {
            case "JOY":
                // JOY는 기존 ChainStateManager 사용
                WorkflowState joyState = stateManager.createState(workflowId);
                initializeJoyState(joyState, request, sessionId, workflowId);
                return joyState;

            case "TOOLUSE":
                // TOOLUSE는 ToolUseStateManager 사용
                ToolUseWorkflowState toolUseState = toolUseStateManager.createState(workflowId);
                initializeToolUseState(toolUseState, request, sessionId, workflowId);
                return toolUseState;

            case "SEMANTICQUERY":
                // SEMANTICQUERY는 SemanticQueryStateManager 사용
                SemanticQueryWorkflowState semanticState = semanticQueryStateManager.createState(workflowId);
                initializeSemanticQueryState(semanticState, request, sessionId, workflowId);
                return semanticState;

            default:
                // 기본값은 기존 ChainStateManager 사용
                WorkflowState defaultState = stateManager.createState(workflowId);
                initializeDefaultState(defaultState, request, sessionId, workflowId, selectedWorkflow);
                return defaultState;
        }
    }

    /**
     * 워크플로우별 최종 State 조회
     */
    private Object getFinalStateForWorkflow(String selectedWorkflow, String workflowId) {
        switch (selectedWorkflow) {
            case "JOY":
                return stateManager.getState(workflowId);
            case "TOOLUSE":
                return toolUseStateManager.getState(workflowId);
            case "SEMANTICQUERY":
                return semanticQueryStateManager.getState(workflowId);
            default:
                return stateManager.getState(workflowId);
        }
    }

    /**
     * 워크플로우별 State 정리
     */
    private void cleanupStateForWorkflow(String selectedWorkflow, String workflowId) {
        switch (selectedWorkflow) {
            case "JOY":
                stateManager.removeState(workflowId);
                break;
            case "TOOLUSE":
                toolUseStateManager.removeState(workflowId);
                break;
            case "SEMANTICQUERY":
                semanticQueryStateManager.removeState(workflowId);
                break;
        }
    }

    /**
     * 모든 State Manager에서 정리 (에러 시 사용)
     */
    private void cleanupAllStates(String workflowId) {
        try {
            stateManager.removeState(workflowId);
        } catch (Exception e) {
            log.warn("ChainStateManager cleanup 실패: {}", e.getMessage());
        }

        try {
            toolUseStateManager.removeState(workflowId);
        } catch (Exception e) {
            log.warn("ToolUseStateManager cleanup 실패: {}", e.getMessage());
        }

        try {
            semanticQueryStateManager.removeState(workflowId);
        } catch (Exception e) {
            log.warn("SemanticQueryStateManager cleanup 실패: {}", e.getMessage());
        }
    }

    /**
     * JOY 워크플로우 State 초기화
     */
    private void initializeJoyState(WorkflowState state, QuviRequestDto request, String sessionId, String workflowId) {
        state.setUserQuestion(request.getUserQuestion());
        state.setUserInfo(UserInfo.builder()
                .userId(request.getUserId())
                .companyId(request.getCompanyId())
                .useInttId(request.getUseInttId())
                .build());
        state.setWorkflowId(workflowId);
        state.setNodeId("node_" + System.currentTimeMillis());
        state.setSelectedWorkflow("JOY");
        state.setIsJoy(true);
        state.setIsApi(false);

        initializeCommonFlags(state);
        log.info("🎉 JOY 워크플로우용 상태 초기화 완료");
    }

    /**
     * TOOLUSE 워크플로우 State 초기화
     */
    private void initializeToolUseState(ToolUseWorkflowState state, QuviRequestDto request, String sessionId, String workflowId) {
        state.setUserQuestion(request.getUserQuestion());
        state.setUserInfo(UserInfo.builder()
                .userId(request.getUserId())
                .companyId(request.getCompanyId())
                .useInttId(request.getUseInttId())
                .build());
        state.setWorkflowId(workflowId);
        state.setNodeId("node_" + System.currentTimeMillis());
        state.setSelectedWorkflow("TOOLUSE");

        // TOOLUSE 특화 초기화
        state.setSafeCount(0);
        state.setQueryResultStatus("");
        state.setSqlError("");
        state.setSqlQuery("");
        state.setQueryResult(new ArrayList<>());
        state.setFinalAnswer("");
        state.setSelectedApi(""); // TOOLUSE는 API 사용
        state.setFString("");

        // 플래그 초기화
        state.setNoData(false);
        state.setFutureDate(false);
        state.setInvalidDate(false);
        state.setQueryError(false);
        state.setQueryChanged(false);
        state.setHasNext(false);

        log.info("🔌 TOOLUSE 워크플로우용 상태 초기화 완료");
    }

    /**
     * SEMANTICQUERY 워크플로우 State 초기화
     */
    private void initializeSemanticQueryState(SemanticQueryWorkflowState state, QuviRequestDto request, String sessionId, String workflowId) {
        state.setUserQuestion(request.getUserQuestion());
        state.setUserInfo(UserInfo.builder()
                .userId(request.getUserId())
                .companyId(request.getCompanyId())
                .useInttId(request.getUseInttId())
                .build());
        state.setWorkflowId(workflowId);
        state.setNodeId("node_" + System.currentTimeMillis());
        state.setSelectedWorkflow("SEMANTICQUERY");

        // SEMANTICQUERY 특화 초기화
        state.setSafeCount(0);
        state.setQueryResultStatus("");
        state.setSqlError("");
        state.setSqlQuery("");
        state.setQueryResult(new ArrayList<>());
        state.setFinalAnswer("");
        state.setSelectedTable(""); // SEMANTICQUERY는 테이블 사용
        state.setFString("");

        // 플래그 초기화
        state.setNoData(false);
        state.setFutureDate(false);
        state.setInvalidDate(false);
        state.setQueryError(false);
        state.setQueryChanged(false);
        state.setHasNext(false);

        log.info("💾 SEMANTICQUERY 워크플로우용 상태 초기화 완료");
    }

    /**
     * 기본 워크플로우 State 초기화 (기존 로직 유지)
     */
    private void initializeDefaultState(WorkflowState state, QuviRequestDto request, String sessionId,
                                        String workflowId, String selectedWorkflow) {
        state.setUserQuestion(request.getUserQuestion());
        state.setUserInfo(UserInfo.builder()
                .userId(request.getUserId())
                .companyId(request.getCompanyId())
                .useInttId(request.getUseInttId())
                .build());
        state.setWorkflowId(workflowId);
        state.setNodeId("node_" + System.currentTimeMillis());
        state.setSelectedWorkflow(selectedWorkflow);

        // 기본 상태 초기화
        state.setSafeCount(0);
        state.setQueryResultStatus("");
        state.setSqlError("");
        state.setSqlQuery("");
        state.setQueryResult(new ArrayList<>());
        state.setFinalAnswer("");
        state.setSelectedTable("");
        state.setFString("");

        initializeCommonFlags(state);
        log.info("⚙️ {} 워크플로우용 기본 상태 초기화 완료", selectedWorkflow);
    }

    /**
     * 공통 플래그 초기화
     */
    private void initializeCommonFlags(WorkflowState state) {
        state.setIsJoy(false);
        state.setNoData(false);
        state.setFutureDate(false);
        state.setInvalidDate(false);
        state.setQueryError(false);
        state.setQueryChanged(false);
        state.setHasNext(false);
    }

    /**
     * State 객체에서 최종 답변 추출
     */
    private String extractFinalAnswer(Object state) {
        if (state instanceof WorkflowState) {
            return ((WorkflowState) state).getFinalAnswer();
        } else if (state instanceof ToolUseWorkflowState) {
            return ((ToolUseWorkflowState) state).getFinalAnswer();
        } else if (state instanceof SemanticQueryWorkflowState) {
            return ((SemanticQueryWorkflowState) state).getFinalAnswer();
        }
        return "처리 중 오류가 발생했습니다.";
    }

    /**
     * 로그 컨텍스트에 최종 상태 업데이트
     */
    private void updateLogContextWithFinalState(ChainLogContext logContext, Object state) {
        if (state instanceof WorkflowState) {
            WorkflowState ws = (WorkflowState) state;
            logContext.setSelectedTable(ws.getSelectedTable());
            logContext.setSqlQuery(ws.getSqlQuery());
            logContext.setFinalAnswer(ws.getFinalAnswer());
            logContext.setUserInfo(ws.getUserInfo());
        } else if (state instanceof ToolUseWorkflowState) {
            ToolUseWorkflowState tus = (ToolUseWorkflowState) state;
            logContext.setSelectedTable(tus.getSelectedApi()); // API명을 selected_table에
            logContext.setSqlQuery(tus.getSqlQuery());
            logContext.setFinalAnswer(tus.getFinalAnswer());
            logContext.setUserInfo(tus.getUserInfo());
        } else if (state instanceof SemanticQueryWorkflowState) {
            SemanticQueryWorkflowState sqs = (SemanticQueryWorkflowState) state;
            logContext.setSelectedTable(sqs.getSelectedTable());
            logContext.setSqlQuery(sqs.getSqlQuery());
            logContext.setFinalAnswer(sqs.getFinalAnswer());
            logContext.setUserInfo(sqs.getUserInfo());
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
     * 선택된 워크플로우를 실행합니다.
     */
    private void executeSelectedWorkflow(String selectedWorkflow, String workflowId) {
        try {
            switch (selectedWorkflow) {
                case "JOY":
                    executeJoyWorkflow(workflowId);
                    break;

                case "TOOLUSE":
                    executeToolUseWorkflow(workflowId);
                    break;
                case "SEMANTICQUERY":
                    executeSemanticQueryWorkflow(workflowId);
                    break;
            }

            chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.INFO,
                    String.format("✅ %s 워크플로우 실행 완료", selectedWorkflow));

        } catch (Exception e) {
            chainLogManager.addLog(workflowId, "CONTROLLER", LogLevel.ERROR,
                    String.format("❌ %s 워크플로우 실행 실패: %s", selectedWorkflow, e.getMessage()), e);
            throw e;
        }
    }

    /**
     * JOY 워크플로우 실행 (일상 대화)
     */
    private void executeJoyWorkflow(String workflowId) {
        log.info("🎉 JOY 워크플로우 실행");
        killjoyWorkflowExecutionContext.executeKilljoyWorkflow(workflowId);
    }

    /**
     * API 워크플로우 실행
     */
    private void executeApiWorkflow(WorkflowState state) {
        log.info("🔌 API 워크플로우 실행");

        workflowContext.executeNode("toolUseNode", state);

        if (state.getInvalidDate() != null && state.getInvalidDate()) {
            log.info("invalid_date 감지 - 워크플로우 종료");
            return;
        }

        workflowContext.executeNode("queryExecutorNode", state);
        handleExecutorResults(state);
    }


    /**
     * TOOLUSE 워크플로우 실행 (ToolUseWorkflowExecutionContext 사용)
     */
    private void executeToolUseWorkflow(String workflowId) {
        log.info("🔌 TOOLUSE 워크플로우 실행 - ToolUse Context 사용");
        toolUseWorkflowContext.executeToolUseWorkflow(workflowId);
    }

    /**
     * SEMANTICQUERY 워크플로우 실행 (SemanticQueryWorkflowExecutionContext 사용)
     */
    private void executeSemanticQueryWorkflow(String workflowId) {
        log.info("💾 SEMANTICQUERY 워크플로우 실행 - SemanticQuery Context 사용");
        semanticQueryWorkflowContext.executeSemanticQueryWorkflow(workflowId);
    }

    /**
     * SQL 워크플로우 실행
     */
    private void executeSqlWorkflow(WorkflowState state) {
        log.info("💾 SQL 워크플로우 실행");

        workflowContext.executeNode("commanderNode", state);

        if (state.getSelectedTable() == null || state.getSelectedTable().trim().isEmpty()) {
            state.setQueryResultStatus("failed");
            state.setSqlError("테이블 선택에 실패했습니다.");
            log.error("Commander에서 테이블 선택 실패");
            return;
        }

        workflowContext.executeNode("opendueNode", state);

        if (state.getIsOpendue() != null && state.getIsOpendue()) {
            workflowContext.executeNode("nl2sqlNode", state);
        } else {
            workflowContext.executeNode("daterNode", state);
            workflowContext.executeNode("nl2sqlNode", state);
        }

        workflowContext.executeNode("queryExecutorNode", state);
        handleExecutorResults(state);
    }

    /**
     * DEFAULT 워크플로우 실행 (기존 로직)
     */
    private void executeDefaultWorkflow(WorkflowState state) {
        log.info("⚙️ DEFAULT 워크플로우 실행");

        // 기존 전체 워크플로우 실행 (checkpoint -> isapi 분기 등)
        workflowContext.executeNode("checkpointNode", state);

        if (state.getIsJoy() != null && state.getIsJoy()) {
            workflowContext.executeNode("killjoyNode", state);
            return;
        }

        workflowContext.executeNode("isApiNode", state);

        if (state.getIsApi() != null && state.getIsApi()) {
            executeApiWorkflow(state);
        } else {
            executeSqlWorkflow(state);
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
                                              Object finalState) {
        Map<String, Object> response = new HashMap<>();

        // 기본 응답
        response.put("status", 200);
        response.put("success", true);
        response.put("retCd", 200);
        response.put("message", "질답 성공");

        // 응답 본문
        Map<String, Object> body = new HashMap<>();

        // 에러 상태 확인
        String finalAnswer = extractFinalAnswer(finalState);
        if (finalAnswer == null || finalAnswer.trim().isEmpty()) {
            finalAnswer = "죄송합니다. 요청을 처리하는 중 오류가 발생했습니다.";
        }
        body.put("answer", finalAnswer);
        body.put("raw_data", extractQueryResult(finalState));
        body.put("session_id", conversationId);
        body.put("chain_id", chainId);
        body.put("recommend", recommendList);
        body.put("is_api", false);
        body.put("date_info", Arrays.asList(extractStartDate(finalState), extractEndDate(finalState)));
        body.put("sql_query", extractSqlQuery(finalState));
        body.put("selected_table", extractSelectedTable(finalState));
        body.put("has_next", extractHasNext(finalState));

        // 프로파일링 정보
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

    private List<?> extractQueryResult(Object state) {
        if (state instanceof WorkflowState) {
            return ((WorkflowState) state).getQueryResult();
        } else if (state instanceof ToolUseWorkflowState) {
            return ((ToolUseWorkflowState) state).getQueryResult();
        } else if (state instanceof SemanticQueryWorkflowState) {
            return ((SemanticQueryWorkflowState) state).getQueryResult();
        }
        return new ArrayList<>();
    }

    private String extractStartDate(Object state) {
        if (state instanceof WorkflowState) {
            return ((WorkflowState) state).getStartDate();
        } else if (state instanceof ToolUseWorkflowState) {
            return ((ToolUseWorkflowState) state).getStartDate();
        } else if (state instanceof SemanticQueryWorkflowState) {
            return ((SemanticQueryWorkflowState) state).getStartDate();
        }
        return null;
    }

    private String extractEndDate(Object state) {
        if (state instanceof WorkflowState) {
            return ((WorkflowState) state).getEndDate();
        } else if (state instanceof ToolUseWorkflowState) {
            return ((ToolUseWorkflowState) state).getEndDate();
        } else if (state instanceof SemanticQueryWorkflowState) {
            return ((SemanticQueryWorkflowState) state).getEndDate();
        }
        return null;
    }

    private String extractSqlQuery(Object state) {
        if (state instanceof WorkflowState) {
            return ((WorkflowState) state).getSqlQuery();
        } else if (state instanceof ToolUseWorkflowState) {
            return ((ToolUseWorkflowState) state).getSqlQuery();
        } else if (state instanceof SemanticQueryWorkflowState) {
            return ((SemanticQueryWorkflowState) state).getSqlQuery();
        }
        return null;
    }

    private String extractSelectedTable(Object state) {
        if (state instanceof WorkflowState) {
            return ((WorkflowState) state).getSelectedTable();
        } else if (state instanceof ToolUseWorkflowState) {
            return ((ToolUseWorkflowState) state).getSelectedApi(); // API명을 selected_table로
        } else if (state instanceof SemanticQueryWorkflowState) {
            return ((SemanticQueryWorkflowState) state).getSelectedTable();
        }
        return null;
    }

    private Boolean extractHasNext(Object state) {
        if (state instanceof WorkflowState) {
            return ((WorkflowState) state).getHasNext() != null ? ((WorkflowState) state).getHasNext() : false;
        } else if (state instanceof ToolUseWorkflowState) {
            return ((ToolUseWorkflowState) state).getHasNext() != null ? ((ToolUseWorkflowState) state).getHasNext() : false;
        } else if (state instanceof SemanticQueryWorkflowState) {
            return ((SemanticQueryWorkflowState) state).getHasNext() != null ? ((SemanticQueryWorkflowState) state).getHasNext() : false;
        }
        return false;
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

                log.info("📊 🔍 Vector DB 전체 - 호출횟수: {}회, 총 소요시간: {}ms, 평균 소요시간: {:.2f}ms",
                        vectorCalls, vectorTotalTime, vectorAvgTime);
            }

            if (llmStats != null) {
                int llmCalls = (Integer) llmStats.getOrDefault("calls", 0);
                long llmTotalTime = (Long) llmStats.getOrDefault("total_time_ms", 0L);
                double llmAvgTime = (Double) llmStats.getOrDefault("avg_time_ms", 0.0);

                log.info("📊 🤖 LLM 전체 - 호출횟수: {}회, 총 소요시간: {}ms, 평균 소요시간: {:.2f}ms",
                        llmCalls, llmTotalTime, llmAvgTime);
            }

            if (dbMainStats != null) {
                int dbMainCalls = (Integer) dbMainStats.getOrDefault("calls", 0);
                long dbMainTotalTime = (Long) dbMainStats.getOrDefault("total_time_ms", 0L);
                double dbMainAvgTime = (Double) dbMainStats.getOrDefault("avg_time_ms", 0.0);

                log.info("📊 🗄️ DB Main 전체 - 호출횟수: {}회, 총 소요시간: {}ms, 평균 소요시간: {:.2f}ms",
                        dbMainCalls, dbMainTotalTime, dbMainAvgTime);
            }

            if (dbPromptStats != null) {
                int dbPromptCalls = (Integer) dbPromptStats.getOrDefault("calls", 0);
                long dbPromptTotalTime = (Long) dbPromptStats.getOrDefault("total_time_ms", 0L);
                double dbPromptAvgTime = (Double) dbPromptStats.getOrDefault("avg_time_ms", 0.0);

                log.info("📊 💾 DB Prompt 전체 - 호출횟수: {}회, 총 소요시간: {}ms, 평균 소요시간: {:.2f}ms",
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

                    log.info("📊 🔧 {} 노드 - 총 호출: {}회, 총 시간: {}ms, 평균: {:.2f}ms",
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
                            log.info("📊   └─ {} {}: {}회, {}ms, 평균 {:.2f}ms",
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

            log.info("📊 ⭐ 전체 요약 - 총 노드 호출: {}회, 프로파일된 시간: {}ms ({:.1f}%), 기타 처리 시간: {}ms",
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