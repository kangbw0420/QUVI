package com.daquv.agent.quvi.util;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.HashMap;

/**
 * chain_id 기반 프로파일링을 위한 유틸리티 클래스
 * ConcurrentHashMap을 사용하여 chain_id별로 독립적인 프로파일링 데이터 관리
 */
@Component
public class RequestProfiler {
    
    private static final Logger log = LoggerFactory.getLogger(RequestProfiler.class);
    
    // chain_id를 키로 사용하는 프로파일링 데이터 관리
    private static final Map<String, ProfileData> profileDataMap = new ConcurrentHashMap<>();
    
    // 프로파일링 활성화 여부 (설정 파일로 제어 가능)
    private boolean enabled;
    
    public RequestProfiler(@Value("${profiling.enabled:false}") boolean profilingEnabled) {
        this.enabled = profilingEnabled;
        
        if (enabled) {
            log.info("RequestProfiler 초기화 - 프로파일링 활성화됨");
        } else {
            log.info("RequestProfiler 초기화 - 프로파일링 비활성화됨 (profiling.enabled: {})", profilingEnabled);
        }
    }
    
    /**
     * 새 요청 시작 - workflowId로 프로파일링 시작
     */
    public void startRequest(String workflowId) {
        if (!enabled || workflowId == null) {
            log.debug("프로파일링이 비활성화되어 요청 시작 스킵 - workflowId: {}", workflowId);
            return;
        }
        
        // chain_id로 프로파일 데이터 초기화
        profileDataMap.put(workflowId, new ProfileData());
        
        log.info("프로파일링 시작 - workflowId: {}", workflowId);
    }

    /**
     * 벡터 DB 호출 프로파일링 (노드 정보 포함)
     */
    public void recordVectorDbCall(String workflowId, double elapsedTime, String nodeId) {
        if (!enabled || workflowId == null) {
            log.debug("벡터 DB 프로파일링 기록 스킵 - enabled: {}, workflowId: {}", enabled, workflowId);
            return;
        }

        if ("unknown".equals(nodeId)) {
            StackTraceElement[] stackTrace = Thread.currentThread().getStackTrace();
            log.warn("🔍 UNKNOWN Vector DB 호출 감지 - workflowId: {}", workflowId);
            log.warn("  호출 스택:");
            for (int i = 1; i <= Math.min(5, stackTrace.length - 1); i++) {
                StackTraceElement element = stackTrace[i];
                log.warn("    {}. {}.{}() ({}:{})",
                        i, element.getClassName(), element.getMethodName(),
                        element.getFileName(), element.getLineNumber());
            }
        }

        log.info("벡터 DB 프로파일링 기록 시작 - workflowId: {}, nodeId: {}, elapsedTime: {}s", workflowId, nodeId, elapsedTime);

        try {
            ProfileData data = profileDataMap.get(workflowId);
            if (data != null) {
                int calls = data.vectorDbCalls.incrementAndGet();
                long totalTime = data.vectorDbTotalTime.addAndGet((long) (elapsedTime * 1000)); // ms로 변환

                // 노드별 통계 업데이트
                data.updateNodeStats(nodeId, "vector_db", elapsedTime);

                log.info("벡터 DB 프로파일링 기록 완료 - workflowId: {}, nodeId: {}, calls: {}, totalTime: {}ms",
                        workflowId, nodeId, calls, totalTime);
            } else {
                log.warn("벡터 DB 프로파일링 데이터가 null임 - workflowId: {}", workflowId);
            }
        } catch (Exception e) {
            log.warn("벡터 DB 프로파일링 기록 중 오류: {}", e.getMessage());
        }
    }

    /**
     * 벡터 DB 호출 프로파일링 (기존 호환성 유지)
     */
    public void recordVectorDbCall(String workflowId, double elapsedTime) {
        recordVectorDbCall(workflowId, elapsedTime, "unknown");
    }

    /**
     * LLM 호출 프로파일링 (노드 정보 포함)
     */
    public void recordLlmCall(String workflowId, double elapsedTime, String nodeId) {
        if (!enabled || workflowId == null) {
            log.debug("LLM 프로파일링 기록 스킵 - enabled: {}, workflowId: {}", enabled, workflowId);
            return;
        }

        if ("unknown".equals(nodeId)) {
            StackTraceElement[] stackTrace = Thread.currentThread().getStackTrace();
            log.warn("🔍 UNKNOWN LLM 호출 감지 - workflowId: {}", workflowId);
            log.warn("  호출 스택:");
            for (int i = 1; i <= Math.min(5, stackTrace.length - 1); i++) {
                StackTraceElement element = stackTrace[i];
                log.warn("    {}. {}.{}() ({}:{})",
                        i, element.getClassName(), element.getMethodName(),
                        element.getFileName(), element.getLineNumber());
            }
        }

        log.info("LLM 프로파일링 기록 시작 - workflowId: {}, nodeId: {}, elapsedTime: {}s", workflowId, nodeId, elapsedTime);

        try {
            ProfileData data = profileDataMap.get(workflowId);
            if (data != null) {
                int calls = data.llmCalls.incrementAndGet();
                long totalTime = data.llmTotalTime.addAndGet((long) (elapsedTime * 1000)); // ms로 변환

                // 노드별 통계 업데이트
                data.updateNodeStats(nodeId, "llm", elapsedTime);

                log.info("LLM 프로파일링 기록 완료 - workflowId: {}, nodeId: {}, calls: {}, totalTime: {}ms",
                        workflowId, nodeId, calls, totalTime);
            } else {
                log.warn("LLM 프로파일링 데이터가 null임 - workflowId: {}", workflowId);
            }
        } catch (Exception e) {
            log.warn("LLM 프로파일링 기록 중 오류: {}", e.getMessage());
        }
    }

    /**
     * DB 호출 프로파일링 (노드 정보 포함)
     */
    public void recordDbCall(String workflowId, double elapsedTime, boolean isPromptDb, String nodeId) {
        if (!enabled || workflowId == null) {
            log.debug("DB 프로파일링 기록 스킵 - enabled: {}, workflowId: {}", enabled, workflowId);
            return;
        }

        if ("unknown".equals(nodeId)) {
            ProfileData data = profileDataMap.get(workflowId);
            if (data != null) {
                // unknown DB 호출이 10회마다 한 번씩만 로깅
                int unknownCount = data.getUnknownDbCallCount();
                if (unknownCount % 10 == 1) {
                    StackTraceElement[] stackTrace = Thread.currentThread().getStackTrace();
                    log.warn("🔍 UNKNOWN DB 호출 감지 #{} - workflowId: {}, isPromptDb: {}",
                            unknownCount, workflowId, isPromptDb);
                    log.warn("  호출 스택:");
                    for (int i = 1; i <= Math.min(5, stackTrace.length - 1); i++) {
                        StackTraceElement element = stackTrace[i];
                        log.warn("    {}. {}.{}() ({}:{})",
                                i, element.getClassName(), element.getMethodName(),
                                element.getFileName(), element.getLineNumber());
                    }
                }
            }
        }

        log.info("DB 프로파일링 기록 시작 - workflowId: {}, nodeId: {}, elapsedTime: {}s, isPromptDb: {}",
                workflowId, nodeId, elapsedTime, isPromptDb);

        try {
            ProfileData data = profileDataMap.get(workflowId);
            if (data != null) {
                String dbType = isPromptDb ? "db_prompt" : "db_main";

                if (isPromptDb) {
                    int calls = data.dbPromptCalls.incrementAndGet();
                    long totalTime = data.dbPromptTotalTime.addAndGet((long) (elapsedTime * 1000)); // ms로 변환
                    log.info("DB Prompt 프로파일링 기록 완료 - workflowId: {}, nodeId: {}, calls: {}, totalTime: {}ms",
                            workflowId, nodeId, calls, totalTime);
                } else {
                    int calls = data.dbMainCalls.incrementAndGet();
                    long totalTime = data.dbMainTotalTime.addAndGet((long) (elapsedTime * 1000)); // ms로 변환
                    log.info("DB Main 프로파일링 기록 완료 - workflowId: {}, nodeId: {}, calls: {}, totalTime: {}ms",
                            workflowId, nodeId, calls, totalTime);
                }

                // 노드별 통계 업데이트
                data.updateNodeStats(nodeId, dbType, elapsedTime);

            } else {
                log.warn("DB 프로파일링 데이터가 null임 - workflowId: {}", workflowId);
            }
        } catch (Exception e) {
            log.warn("DB 프로파일링 기록 중 오류: {}", e.getMessage());
        }
    }
    
    /**
     * 프로파일 결과 조회
     */
    public Map<String, Object> getProfile(String workflowId) {
        if (!enabled) {
            log.debug("프로파일링이 비활성화되어 있음");
            return new HashMap<>();
        }
        
        ProfileData data = profileDataMap.get(workflowId);
        if (data == null) {
            log.warn("프로파일 데이터가 null임 - workflowId: {}", workflowId);
            return new HashMap<>();
        }
        
        log.info("프로파일 데이터 조회 - workflowId: {}, vectorDbCalls: {}, llmCalls: {}, dbMainCalls: {}, dbPromptCalls: {}",
                workflowId, data.vectorDbCalls.get(), data.llmCalls.get(), data.dbMainCalls.get(), data.dbPromptCalls.get());
        
        Map<String, Object> result = new ConcurrentHashMap<>();
        
        // vector_db
        result.put("vector_db", createProfileEntry(
            data.vectorDbCalls.get(),
            data.vectorDbTotalTime.get()
        ));
        
        // llm
        result.put("llm", createProfileEntry(
            data.llmCalls.get(),
            data.llmTotalTime.get()
        ));
        
        // db_main (기존 db_normal)
        result.put("db_main", createProfileEntry(
            data.dbMainCalls.get(),
            data.dbMainTotalTime.get()
        ));
        
        // db_prompt
        result.put("db_prompt", createProfileEntry(
            data.dbPromptCalls.get(),
            data.dbPromptTotalTime.get()
        ));
        
        log.info("프로파일 결과 생성 완료 - workflowId: {}, result: {}", workflowId, result);
        return result;
    }
    
    /**
     * 프로파일 데이터 삭제
     */
    public void clearProfile(String workflowId) {
        if (!enabled) {
            return;
        }
        
        try {
            profileDataMap.remove(workflowId);
            log.debug("프로파일링 데이터 삭제 - workflowId: {}", workflowId);
        } catch (Exception e) {
            log.warn("프로파일링 데이터 삭제 중 오류: {}", e.getMessage());
        }
    }
    
    /**
     * 프로파일 엔트리 생성
     */
    private Map<String, Object> createProfileEntry(int calls, long totalTimeMs) {
        Map<String, Object> entry = new ConcurrentHashMap<>();
        entry.put("calls", calls);
        entry.put("total_time_ms", totalTimeMs);
        entry.put("avg_time_ms", calls > 0 ? (double) totalTimeMs / calls : 0.0);
        return entry;
    }
    
    /**
     * 프로파일링 데이터를 담는 내부 클래스
     */
    private static class ProfileData {
        // 벡터 DB
        private final AtomicInteger vectorDbCalls = new AtomicInteger(0);
        private final AtomicLong vectorDbTotalTime = new AtomicLong(0);

        // LLM
        private final AtomicInteger llmCalls = new AtomicInteger(0);
        private final AtomicLong llmTotalTime = new AtomicLong(0);

        // DB (일반)
        private final AtomicInteger dbMainCalls = new AtomicInteger(0);
        private final AtomicLong dbMainTotalTime = new AtomicLong(0);

        // DB (프롬프트)
        private final AtomicInteger dbPromptCalls = new AtomicInteger(0);
        private final AtomicLong dbPromptTotalTime = new AtomicLong(0);
        private final AtomicInteger unknownDbCallCount = new AtomicInteger(0);
        // 워크플로우 노드별 상세 통계 (nodeId -> {type -> stats})
        private final Map<String, Map<String, NodeStats>> workflowNodeStats = new ConcurrentHashMap<>();

        public int getUnknownDbCallCount() {
            return unknownDbCallCount.incrementAndGet();
        }

        /**
         * 워크플로우 노드별 통계 업데이트
         */
        private void updateNodeStats(String nodeId, String type, double elapsedTime) {
            workflowNodeStats.computeIfAbsent(nodeId, k -> new ConcurrentHashMap<>())
                    .computeIfAbsent(type, k -> new NodeStats())
                    .addCall(elapsedTime);
        }

        /**
         * 워크플로우 노드별 통계 반환
         */
        private Map<String, Object> getWorkflowNodeStats() {
            Map<String, Object> result = new HashMap<>();

            for (Map.Entry<String, Map<String, NodeStats>> nodeEntry : workflowNodeStats.entrySet()) {
                String nodeId = nodeEntry.getKey();
                Map<String, NodeStats> typeStats = nodeEntry.getValue();

                Map<String, Object> nodeData = new HashMap<>();

                // 각 노드의 타입별 통계
                for (Map.Entry<String, NodeStats> typeEntry : typeStats.entrySet()) {
                    String type = typeEntry.getKey();
                    NodeStats stats = typeEntry.getValue();

                    Map<String, Object> typeData = new HashMap<>();
                    typeData.put("calls", stats.calls.get());
                    typeData.put("total_time_ms", stats.totalTime.get());
                    typeData.put("avg_time_ms", stats.getAverageTime());

                    nodeData.put(type, typeData);
                }

                // 노드 전체 통계 (모든 타입 합계)
                int totalCalls = 0;
                long totalTime = 0;
                for (NodeStats stats : typeStats.values()) {
                    totalCalls += stats.calls.get();
                    totalTime += stats.totalTime.get();
                }

                Map<String, Object> nodeSummary = new HashMap<>();
                nodeSummary.put("total_calls", totalCalls);
                nodeSummary.put("total_time_ms", totalTime);
                nodeSummary.put("avg_time_ms", totalCalls > 0 ? (double) totalTime / totalCalls : 0.0);
                nodeSummary.put("details", nodeData);

                result.put(nodeId, nodeSummary);
            }

            return result;
        }

        /**
         * 노드별 통계를 담는 내부 클래스
         */
        private static class NodeStats {
            private final AtomicInteger calls = new AtomicInteger(0);
            private final AtomicLong totalTime = new AtomicLong(0);

            private void addCall(double elapsedTime) {
                calls.incrementAndGet();
                totalTime.addAndGet((long) (elapsedTime * 1000)); // ms로 변환
            }

            private double getAverageTime() {
                int callCount = calls.get();
                return callCount > 0 ? (double) totalTime.get() / callCount : 0.0;
            }
        }

    }
} 