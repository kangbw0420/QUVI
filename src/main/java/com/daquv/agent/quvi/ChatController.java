package com.daquv.agent.quvi;

import com.daquv.agent.quvi.dto.LogLevel;
import com.daquv.agent.quvi.dto.QuviRequestDto;
import com.daquv.agent.quvi.llmadmin.SessionService;
import com.daquv.agent.quvi.llmadmin.WorkflowService;
import com.daquv.agent.quvi.logging.WorkflowLogContext;
import com.daquv.agent.quvi.logging.WorkflowLogManager;
import com.daquv.agent.quvi.requests.VectorRequest;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.util.StatisticsUtils;
import com.daquv.agent.quvi.util.ResponseUtils;
import com.daquv.agent.quvi.workflow.WorkflowExecutionManagerService;
import com.daquv.agent.workflow.SupervisorNode;
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
                    Map<String, Object> hilResponse = ResponseUtils.buildHilWaitingResponse(
                            workflowExecutionManagerService, sessionService.getOrCreateSessionId(request), workflowId, totalTime, selectedWorkflow, requestProfiler, "HIL 대기 중");

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

            // 10. Chain 완료
            String finalAnswer = workflowExecutionManagerService.extractFinalAnswer(selectedWorkflow, workflowId);
            workflowService.completeWorkflow(workflowId, finalAnswer);

            // 로그 컨텍스트에 최종 결과 저장
            chainLogManager.updateLogContextWithFinalState(logContext, selectedWorkflow, workflowId, request, workflowExecutionManagerService);

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

            Map<String, Object> errorResponse = ResponseUtils.buildErrorResponse(e.getMessage(), "질답 실패");
            return ResponseEntity.ok(errorResponse);
        }
    }

    public String selectWorkflowUsingSupervisor(String userQuestion, String workflowId) {
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
     * 추천 질문 검색
     */
    public List<String> getRecommendations(String userQuestion, String workflowId) {
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

    private String removeHttpProtocol(String text) {
        if (text == null) {
            return null;
        }

        // "java.lang" 을 "java_lang" 으로 치환
        return text.replaceAll("java\\.lang", "java_lang");
    }
} 