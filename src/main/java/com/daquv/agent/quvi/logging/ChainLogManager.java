package com.daquv.agent.quvi.logging;

import com.daquv.agent.quvi.dto.AlertType;
import com.daquv.agent.quvi.dto.ChainLogEntry;
import com.daquv.agent.quvi.dto.LogAlertRule;
import com.daquv.agent.quvi.dto.LogLevel;
import com.daquv.agent.quvi.llmadmin.WorkflowService;
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
public class ChainLogManager {

    private final Map<String, ChainLogContext> chainLogs = new ConcurrentHashMap<>();
    private final List<LogAlertRule> alertRules = new CopyOnWriteArrayList<>();
    private final LogAlertService alertService;
    private final WorkflowService workflowService;
    public ChainLogManager(LogAlertService alertService, WorkflowService workflowService) {
        this.alertService = alertService;
        this.workflowService = workflowService;
    }

    /**
     * 체인 로그 컨텍스트 생성
     */
    public ChainLogContext createChainLog(String chainId, String userId, String userQuestion) {
        if (chainLogs.containsKey(chainId)) {
            log.debug("기존 체인 로그 컨텍스트 교체 - chainId: {}", chainId);
        }

        ChainLogContext context = new ChainLogContext(chainId, userId, userQuestion);
        chainLogs.put(chainId, context);

        log.info("🔗 체인 로그 컨텍스트 생성 - chainId: {}, userId: {}", chainId, userId);
        return context;
    }

    /**
     * 체인별 로그 추가
     */
    public void addLog(String chainId, String nodeId, LogLevel level, String message) {
        ChainLogContext context = chainLogs.get(chainId);
        if (context == null) {
            log.warn("체인 로그 컨텍스트를 찾을 수 없습니다: {}", chainId);
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
    public void addLog(String chainId, String nodeId, LogLevel level, String message, Exception exception) {
        ChainLogContext context = chainLogs.get(chainId);
        if (context == null) {
            log.warn("체인 로그 컨텍스트를 찾을 수 없습니다: {}", chainId);
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
    public void completeWorkflow(String chainId, boolean success) {
        ChainLogContext context = chainLogs.get(chainId);
        if (context == null) {
            log.warn("체인 로그 컨텍스트를 찾을 수 없습니다: {}", chainId);
            return;
        }

        // ERROR 로그가 있으면 실패로 판단
        boolean hasErrors = context.getLogEntries().stream()
                .anyMatch(entry -> entry.getLevel() == LogLevel.ERROR);

        // 파라미터로 받은 success와 에러 로그 존재 여부를 조합
        boolean actualSuccess = success && !hasErrors;

        context.complete(actualSuccess);

        String chainLogText = buildChainLogText(context);

        try {
            // Chain 테이블에 로그 저장 - 트랜잭션 내에서 실행
            if (actualSuccess) {
                workflowService.updateChainLog(chainId, chainLogText);
                log.info("✅ Chain 로그 저장 성공 - chainId: {}", chainId);
            } else {
                workflowService.markChainError(chainId, "Workflow execution failed", chainLogText);
                log.info("❌ Chain 에러 로그 저장 성공 - chainId: {}", chainId);
            }
        } catch (Exception e) {
            log.error("❌ Chain 로그 DB 저장 실패 - chainId: {}, error: {}", chainId, e.getMessage(), e);
            // 저장 실패해도 알림은 보내기
        }

        // 실패한 경우에만 Flow 알림 전송 (비동기)
        if (!actualSuccess) {
            sendChainErrorAlertAsync(chainId, context, chainLogText);
        }

        // 메모리에서 제거 (옵션)
        chainLogs.remove(chainId);

        log.info("🔗 체인 완료 - chainId: {}, success: {}, 총 로그 수: {}, 에러 로그: {}",
                chainId, actualSuccess, context.getLogEntries().size(), hasErrors);
    }

    private void sendChainErrorAlertAsync(String chainId, ChainLogContext context, String chainLogText) {
        CompletableFuture.runAsync(() -> {
            try {
                sendChainErrorAlert(chainId, context, chainLogText);
            } catch (Exception e) {
                log.error("Flow 알림 전송 실패 - chainId: {}, error: {}", chainId, e.getMessage(), e);
            }
        });
    }

    /**
     * 특정 체인에 ERROR 레벨 로그가 있는지 확인
     */
    public boolean hasErrorLogs(String chainId) {
        ChainLogContext context = chainLogs.get(chainId);
        if (context == null) {
            return false;
        }

        return context.getLogEntries().stream()
                .anyMatch(entry -> entry.getLevel() == LogLevel.ERROR);
    }

    /**
     * 체인 로그를 텍스트로 변환
     */
    private String buildChainLogText(ChainLogContext context) {
        StringBuilder logText = new StringBuilder();

        logText.append("=== Chain Log ===\n");
        logText.append("Chain ID: ").append(context.getChainId()).append("\n");
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
    private void sendChainErrorAlert(String chainId, ChainLogContext context, String chainLogText) {
        try {
            // Flow 알림 규칙 생성
            LogAlertRule chainErrorRule = LogAlertRule.builder()
                    .ruleName("CHAIN_ERROR_ALERT")
                    .description("체인 실행 실패 알림")
                    .alertType(AlertType.ERROR)
                    .enabled(true)
                    .build();

            // 더미 로그 엔트리 생성 (Flow 알림용)
            ChainLogEntry errorEntry = ChainLogEntry.builder()
                    .timestamp(LocalDateTime.now())
                    .nodeId("CHAIN")
                    .level(LogLevel.ERROR)
                    .message("체인 실행 실패")
                    .data(chainLogText)
                    .build();

            alertService.sendChainErrorAlert(chainErrorRule, chainId, context, errorEntry, chainLogText);

        } catch (Exception e) {
            log.error("체인 에러 Flow 알림 전송 실패 - chainId: {}, error: {}", chainId, e.getMessage(), e);
        }
    }
}