package com.daquv.agent.quvi;

import com.daquv.agent.quvi.dto.LogLevel;
import com.daquv.agent.quvi.dto.QuviHilResumeDto;
import com.daquv.agent.quvi.llmadmin.WorkflowService;
import com.daquv.agent.quvi.logging.WorkflowLogContext;
import com.daquv.agent.quvi.logging.WorkflowLogManager;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.workflow.WorkflowExecutionManagerService;
import com.daquv.agent.workflow.dto.UserInfo;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import javax.servlet.http.HttpServletRequest;
import java.util.*;
import com.daquv.agent.quvi.util.StatisticsUtils;
import com.daquv.agent.quvi.util.ResponseUtils;

@RestController
public class ResumeController {

    private static final Logger log = LoggerFactory.getLogger(ResumeController.class);

    private final WorkflowService workflowService;
    private final WorkflowLogManager chainLogManager;
    private final RequestProfiler requestProfiler;

    @Autowired
    private WorkflowExecutionManagerService workflowExecutionManagerService;

    public ResumeController(WorkflowService workflowService, 
                           WorkflowLogManager chainLogManager,
                           RequestProfiler requestProfiler) {
        this.workflowService = workflowService;
        this.chainLogManager = chainLogManager;
        this.requestProfiler = requestProfiler;
    }

    /**
     * HIL 재개 처리를 위한 엔드포인트
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
            WorkflowLogContext logContext = chainLogManager.resumeWorkflowLog(workflowId);

            chainLogManager.addLog(workflowId, "RESUME_CONTROLLER", LogLevel.INFO,
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
            updateLogContextWithFinalState(logContext, workflowType, workflowId);

            // 응답 생성
            long totalTime = System.currentTimeMillis() - startTime;
            Map<String, Object> response = ResponseUtils.buildResponse(
                    workflowExecutionManagerService, request.getSessionId(), workflowId, new ArrayList<>(), totalTime, workflowType, requestProfiler, "HIL 재개 성공");

            StatisticsUtils.logNodeExecutionStatistics(log, chainLogManager, workflowId, totalTime, requestProfiler.getProfile(workflowId), "HIL_STATISTICS");

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
                StatisticsUtils.logNodeExecutionStatistics(log, chainLogManager, workflowId, totalTime, requestProfiler.getProfile(workflowId), "HIL_STATISTICS");
                chainLogManager.completeWorkflow(workflowId, false);
                requestProfiler.clearProfile(workflowId);
                workflowExecutionManagerService.cleanupAllStates(workflowId);
            }

            Map<String, Object> errorResponse = buildErrorResponse(e.getMessage());
            return ResponseEntity.ok(errorResponse);
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
        response.put("message", "HIL 재개 실패");

        Map<String, Object> body = new HashMap<>();
        body.put("answer", "죄송합니다. HIL 재개 처리 중 오류가 발생했습니다.");
        body.put("error", errorMessage);

        response.put("body", body);
        return response;
    }
} 