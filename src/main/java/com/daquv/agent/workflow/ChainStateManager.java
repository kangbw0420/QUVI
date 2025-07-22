package com.daquv.agent.workflow;

import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;

@Component
@Slf4j
public class ChainStateManager {
    
    // Chain ID별 State 저장소
    private final ConcurrentHashMap<String, WorkflowState> chainStates = new ConcurrentHashMap<>();
    
    // State 생존 시간 관리
    private final ConcurrentHashMap<String, Long> stateTimestamps = new ConcurrentHashMap<>();
    
    // State 만료 시간 (30분)
    private static final long STATE_EXPIRY_MS = 30 * 60 * 1000;
    
    /**
     * 새 State 생성
     */
    public WorkflowState createState(String workflowId) {
        WorkflowState state = WorkflowState.builder()
                .workflowId(workflowId)
                .nodeId("node_" + System.currentTimeMillis())
                .safeCount(0)
                .queryError(false)
                .isJoy(false)
                .noData(false)
                .futureDate(false)
                .invalidDate(false)
                .queryChanged(false)
                .hasNext(false)
                .build();
        
        chainStates.put(workflowId, state);
        stateTimestamps.put(workflowId, System.currentTimeMillis());
        
        log.info("State 생성 - chainId: {}", workflowId);
        return state;
    }
    
    /**
     * State 조회
     */
    public WorkflowState getState(String chainId) {
        if (chainId == null) {
            return null;
        }
        
        // 만료 체크
        Long timestamp = stateTimestamps.get(chainId);
        if (timestamp != null && (System.currentTimeMillis() - timestamp) > STATE_EXPIRY_MS) {
            removeState(chainId);
            return null;
        }
        
        return chainStates.get(chainId);
    }
    
    /**
     * State 업데이트
     */
    public void updateState(String chainId, WorkflowState state) {
        if (chainId != null && state != null) {
            chainStates.put(chainId, state);
            stateTimestamps.put(chainId, System.currentTimeMillis());
        }
    }
    
    /**
     * State 제거
     */
    public void removeState(String chainId) {
        if (chainId != null) {
            chainStates.remove(chainId);
            stateTimestamps.remove(chainId);
            log.debug("State 제거 - chainId: {}", chainId);
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