package com.daquv.agent.quvi.logging;

import com.daquv.agent.quvi.dto.AlertType;
import com.daquv.agent.quvi.dto.ChainLogEntry;
import com.daquv.agent.quvi.dto.LogAlertRule;
import com.daquv.agent.quvi.dto.LogLevel;
import com.daquv.agent.quvi.llmadmin.WorkflowService;
import com.daquv.agent.quvi.workflow.WorkflowExecutionManagerService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import javax.transaction.Transactional;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * 체인별 로그 관리 및 알림 시스템
 */
@Slf4j
@Component
public class WorkflowLogManager {

    private final Map<String, WorkflowLogContext> workflowLogs = new ConcurrentHashMap<>();
    private final List<LogAlertRule> alertRules = new CopyOnWriteArrayList<>();
    private final LogAlertService alertService;
    private final WorkflowService workflowService;
    public WorkflowLogManager(LogAlertService alertService, WorkflowService workflowService) {
        this.alertService = alertService;
        this.workflowService = workflowService;
    }

    /**
     * 체인 로그 컨텍스트 생성
     */
    public WorkflowLogContext createWorkflowLog(String workflowId, String userId, String userQuestion) {
        if (workflowLogs.containsKey(workflowId)) {
            log.debug("기존 체인 로그 컨텍스트 교체 - workflowId: {}", workflowId);
        }

        WorkflowLogContext context = new WorkflowLogContext(workflowId, userId, userQuestion);
        workflowLogs.put(workflowId, context);

        log.info("🔗 체인 로그 컨텍스트 생성 - workflowId: {}, userId: {}", workflowId, userId);
        return context;
    }

    /**
     * HIL 후 체인 로그 재개
     */
    public WorkflowLogContext resumeWorkflowLog(String workflowId) {
        WorkflowLogContext context = workflowLogs.get(workflowId);
        if (context == null) {
            log.warn("재개할 체인 로그 컨텍스트를 찾을 수 없습니다: {}", workflowId);
            // 컨텍스트가 없는 경우 기본 컨텍스트 생성
            context = new WorkflowLogContext(workflowId, "unknown", "HIL 재개");
            workflowLogs.put(workflowId, context);
        }

        // HIL 재개 로그 추가
        addLog(workflowId, "CONTROLLER", LogLevel.INFO, "🔄 HIL 워크플로우 재개");

        log.info("🔄 체인 로그 재개 - workflowId: {}", workflowId);
        return context;
    }

    /**
     * 체인별 로그 추가
     */
    public void addLog(String workflowId, String nodeId, LogLevel level, String message) {
        WorkflowLogContext context = workflowLogs.get(workflowId);
        if (context == null) {
            log.warn("체인 로그 컨텍스트를 찾을 수 없습니다: {}", workflowId);
            return;
        }

        ChainLogEntry entry = ChainLogEntry.builder()
                .timestamp(LocalDateTime.now())
                .nodeId(nodeId)
                .level(level)
                .message(message)
                .build();

        context.addLogEntry(entry);
    }

    /**
     * 체인별 로그 추가 (예외 포함)
     */
    public void addLog(String workflowId, String nodeId, LogLevel level, String message, Exception exception) {
        WorkflowLogContext context = workflowLogs.get(workflowId);
        if (context == null) {
            log.warn("체인 로그 컨텍스트를 찾을 수 없습니다: {}", workflowId);
            return;
        }

        ChainLogEntry entry = ChainLogEntry.builder()
                .timestamp(LocalDateTime.now())
                .nodeId(nodeId)
                .level(level)
                .message(message)
                .exception(exception)
                .build();

        context.addLogEntry(entry);
    }

    /**
     * 체인 완료 처리
     */

    @Transactional
    public void completeWorkflow(String workflowId, boolean success) {
        WorkflowLogContext context = workflowLogs.get(workflowId);
        if (context == null) {
            log.warn("체인 로그 컨텍스트를 찾을 수 없습니다: {}", workflowId);
            return;
        }

        // ERROR 로그가 있으면 실패로 판단
        boolean hasErrors = context.getLogEntries().stream()
                .anyMatch(entry -> entry.getLevel() == LogLevel.ERROR);

        // 파라미터로 받은 success와 에러 로그 존재 여부를 조합
        boolean actualSuccess = success && !hasErrors;

        context.complete(actualSuccess);

        String workflowLogText = buildChainLogText(context);

        try {
            // Workflow 테이블에 로그 저장 - 트랜잭션 내에서 실행
            if (actualSuccess) {
                workflowService.updateWorkflowLog(workflowId, workflowLogText);
                log.info("✅ Chain 로그 저장 성공 - workflowId: {}", workflowId);
            } else {
                workflowService.markWorkflowError(workflowId, "Workflow execution failed", workflowLogText);
                log.info("❌ Chain 에러 로그 저장 성공 - workflowId: {}", workflowId);
            }
        } catch (Exception e) {
            log.error("❌ Chain 로그 DB 저장 실패 - workflowId: {}, error: {}", workflowId, e.getMessage(), e);
            // 저장 실패해도 알림은 보내기
        }

        // 실패한 경우에만 Flow 알림 전송 (비동기)
        if (!actualSuccess) {
            sendWorkflowErrorAlertAsync(workflowId, context, workflowLogText);
        }

        // 메모리에서 제거 (옵션)
        workflowLogs.remove(workflowId);

        log.info("🔗 체인 완료 - workflowId: {}, success: {}, 총 로그 수: {}, 에러 로그: {}",
                workflowId, actualSuccess, context.getLogEntries().size(), hasErrors);
    }

    private void sendWorkflowErrorAlertAsync(String workflowId, WorkflowLogContext context, String chainLogText) {
        CompletableFuture.runAsync(() -> {
            try {
                sendWorkflowErrorAlert(workflowId, context, chainLogText);
            } catch (Exception e) {
                log.error("Flow 알림 전송 실패 - workflowId: {}, error: {}", workflowId, e.getMessage(), e);
            }
        });
    }

    /**
     * 특정 체인에 ERROR 레벨 로그가 있는지 확인
     */
    public boolean hasErrorLogs(String workflowId) {
        WorkflowLogContext context = workflowLogs.get(workflowId);
        if (context == null) {
            return false;
        }

        return context.getLogEntries().stream()
                .anyMatch(entry -> entry.getLevel() == LogLevel.ERROR);
    }

    /**
     * 체인 로그를 텍스트로 변환
     */
    private String buildChainLogText(WorkflowLogContext context) {
        StringBuilder logText = new StringBuilder();

        logText.append("=== Workflow Log ===\n");
        logText.append("Workflow ID: ").append(context.getWorkflowId()).append("\n");
        logText.append("User ID: ").append(context.getUserId()).append("\n");
        logText.append("Question: ").append(context.getUserQuestion()).append("\n");
        logText.append("Start Time: ").append(context.getStartTime()).append("\n");
        logText.append("End Time: ").append(context.getEndTime()).append("\n");
        logText.append("Duration: ").append(context.getDurationMs()).append("ms\n");
        logText.append("Success: ").append(context.isSuccess()).append("\n\n");

        logText.append("=== Log Entries ===\n");
        for (ChainLogEntry entry : context.getLogEntries()) {
            logText.append("[").append(entry.getTimestamp()).append("] ");
            logText.append("[").append(entry.getLevel()).append("] ");
            logText.append("[").append(entry.getNodeId()).append("] ");
            logText.append(entry.getMessage()).append("\n");

            if (entry.getException() != null) {
                logText.append("Exception: ").append(removeHttpProtocol(entry.getException().getMessage())).append("\n");
                if (entry.getStackTrace() != null) {
                    logText.append("Stack Trace:\n").append(removeHttpProtocol(entry.getStackTrace())).append("\n");
                }
            }
            logText.append("\n");
        }

        return logText.toString();
    }

    private String removeHttpProtocol(String text) {
        if (text == null) {
            return null;
        }

        // "java.lang" 을 "java_lang" 으로 치환
        return text.replaceAll("java\\.lang", "java_lang");
    }

    /**
     * 체인 에러 Flow 알림 전송
     */
    private void sendWorkflowErrorAlert(String workflowId, WorkflowLogContext context, String workflowLogText) {
        try {
            // Flow 알림 규칙 생성
            LogAlertRule chainErrorRule = LogAlertRule.builder()
                    .ruleName("WORKFLOW_ERROR_ALERT")
                    .description("체인 실행 실패 알림")
                    .alertType(AlertType.ERROR)
                    .enabled(true)
                    .build();

            // 더미 로그 엔트리 생성 (Flow 알림용)
            ChainLogEntry errorEntry = ChainLogEntry.builder()
                    .timestamp(LocalDateTime.now())
                    .nodeId("WORKFLOW")
                    .level(LogLevel.ERROR)
                    .message("체인 실행 실패")
                    .data(workflowLogText)
                    .build();

            alertService.sendChainErrorAlert(chainErrorRule, workflowId, context, errorEntry, workflowLogText);

        } catch (Exception e) {
            log.error("체인 에러 Flow 알림 전송 실패 - workflowId: {}, error: {}", workflowId, e.getMessage(), e);
        }
    }

    /**
     * 워크플로우 실행 후 로그 컨텍스트에 최종 상태 업데이트 (request는 null 허용)
     */
    public void updateLogContextWithFinalState(WorkflowLogContext logContext, String selectedWorkflow, String workflowId, Object request, WorkflowExecutionManagerService workflowExecutionManagerService) {
        try {
            String selectedTable = workflowExecutionManagerService.extractSelectedTable(selectedWorkflow, workflowId);
            String sqlQuery = workflowExecutionManagerService.extractSqlQuery(selectedWorkflow, workflowId);
            String finalAnswer = workflowExecutionManagerService.extractFinalAnswer(selectedWorkflow, workflowId);

            logContext.setSelectedTable(selectedTable);
            logContext.setSqlQuery(sqlQuery);
            logContext.setFinalAnswer(finalAnswer);

            if (!"JOY".equals(selectedWorkflow)) {
                // request가 null이 아니면 넘기고, null이면 null로 넘김
                com.daquv.agent.workflow.dto.UserInfo userInfo = workflowExecutionManagerService.extractUserInfo(selectedWorkflow, workflowId, (com.daquv.agent.quvi.dto.QuviRequestDto) request);
                logContext.setUserInfo(userInfo);
            } else {
                log.debug("JOY 워크플로우는 UserInfo를 로그 컨텍스트에 설정하지 않습니다.");
            }

        } catch (Exception e) {
            log.error("로그 컨텍스트 업데이트 실패 - selectedWorkflow: {}, workflowId: {}", selectedWorkflow, workflowId, e);
        }
    }
}