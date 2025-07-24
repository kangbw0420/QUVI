package com.daquv.agent.workflow.tooluse;

import com.daquv.agent.workflow.WorkflowState;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;

@Component
@Slf4j
public class ToolUseStateManager {
    // Chain ID별 State 저장소
    private final ConcurrentHashMap<String, ToolUseWorkflowState> chainStates = new ConcurrentHashMap<>();

    // State 생존 시간 관리
    private final ConcurrentHashMap<String, Long> stateTimestamps = new ConcurrentHashMap<>();

    // State 만료 시간 (30분)
    private static final long STATE_EXPIRY_MS = 30 * 60 * 1000;

    /**
     * 새 State 생성
     */
    public ToolUseWorkflowState createState(String workflowId) {
        ToolUseWorkflowState state = ToolUseWorkflowState.builder()
                .workflowId(workflowId)
                .nodeId("node_" + System.currentTimeMillis())
                .safeCount(0)
                .noData(false)
                .futureDate(false)
                .invalidDate(false)
                .hasNext(false)
                .build();

        chainStates.put(workflowId, state);
        stateTimestamps.put(workflowId, System.currentTimeMillis());

        log.info("State 생성 - workflowId: {}", workflowId);
        return state;
    }

    /**
     * State 조회
     */
    public ToolUseWorkflowState getState(String workflowId) {
        if (workflowId == null) {
            return null;
        }

        // 만료 체크
        Long timestamp = stateTimestamps.get(workflowId);
        if (timestamp != null && (System.currentTimeMillis() - timestamp) > STATE_EXPIRY_MS) {
            removeState(workflowId);
            return null;
        }

        return chainStates.get(workflowId);
    }

    /**
     * State 업데이트
     */
    public void updateState(String workflowId, ToolUseWorkflowState state) {
        if (workflowId != null && state != null) {
            chainStates.put(workflowId, state);
            stateTimestamps.put(workflowId, System.currentTimeMillis());
        }
    }

    /**
     * State 제거
     */
    public void removeState(String workflowId) {
        if (workflowId != null) {
            chainStates.remove(workflowId);
            stateTimestamps.remove(workflowId);
            log.debug("State 제거 - workflowId: {}", workflowId);
        }
    }

    /**
     * 만료된 State 정리
     */
    @Scheduled(fixedRate = 300000) // 5분마다
    public void cleanupExpiredStates() {
        long currentTime = System.currentTimeMillis();
        List<String> expiredChainIds = new ArrayList<>();

        stateTimestamps.entrySet().forEach(entry -> {
            if ((currentTime - entry.getValue()) > STATE_EXPIRY_MS) {
                expiredChainIds.add(entry.getKey());
            }
        });

        expiredChainIds.forEach(this::removeState);

        if (!expiredChainIds.isEmpty()) {
            log.info("만료된 State {} 개 정리", expiredChainIds.size());
        }
    }
}
