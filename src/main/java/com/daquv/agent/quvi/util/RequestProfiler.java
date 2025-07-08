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
     * 새 요청 시작 - chain_id로 프로파일링 시작
     */
    public void startRequest(String chainId) {
        if (!enabled || chainId == null) {
            log.debug("프로파일링이 비활성화되어 요청 시작 스킵 - chainId: {}", chainId);
            return;
        }
        
        // chain_id로 프로파일 데이터 초기화
        profileDataMap.put(chainId, new ProfileData());
        
        log.info("프로파일링 시작 - chainId: {}", chainId);
    }
    
    /**
     * 벡터 DB 호출 프로파일링
     */
    public void recordVectorDbCall(String chainId, double elapsedTime) {
        if (!enabled || chainId == null) {
            log.debug("벡터 DB 프로파일링 기록 스킵 - enabled: {}, chainId: {}", enabled, chainId);
            return;
        }
        
        log.info("벡터 DB 프로파일링 기록 시작 - chainId: {}, elapsedTime: {}s", chainId, elapsedTime);
        
        try {
            ProfileData data = profileDataMap.get(chainId);
            if (data != null) {
                int calls = data.vectorDbCalls.incrementAndGet();
                long totalTime = data.vectorDbTotalTime.addAndGet((long) (elapsedTime * 1000)); // ms로 변환
                log.info("벡터 DB 프로파일링 기록 완료 - chainId: {}, calls: {}, totalTime: {}ms", chainId, calls, totalTime);
            } else {
                log.warn("벡터 DB 프로파일링 데이터가 null임 - chainId: {}", chainId);
            }
        } catch (Exception e) {
            log.warn("벡터 DB 프로파일링 기록 중 오류: {}", e.getMessage());
        }
    }
    
    /**
     * LLM 호출 프로파일링
     */
    public void recordLlmCall(String chainId, double elapsedTime) {
        if (!enabled || chainId == null) {
            log.debug("LLM 프로파일링 기록 스킵 - enabled: {}, chainId: {}", enabled, chainId);
            return;
        }
        
        log.info("LLM 프로파일링 기록 시작 - chainId: {}, elapsedTime: {}s", chainId, elapsedTime);
        
        try {
            ProfileData data = profileDataMap.get(chainId);
            if (data != null) {
                int calls = data.llmCalls.incrementAndGet();
                long totalTime = data.llmTotalTime.addAndGet((long) (elapsedTime * 1000)); // ms로 변환
                log.info("LLM 프로파일링 기록 완료 - chainId: {}, calls: {}, totalTime: {}ms", chainId, calls, totalTime);
            } else {
                log.warn("LLM 프로파일링 데이터가 null임 - chainId: {}", chainId);
            }
        } catch (Exception e) {
            log.warn("LLM 프로파일링 기록 중 오류: {}", e.getMessage());
        }
    }
    
    /**
     * DB 호출 프로파일링
     */
    public void recordDbCall(String chainId, double elapsedTime, boolean isPromptDb) {
        if (!enabled || chainId == null) {
            log.debug("DB 프로파일링 기록 스킵 - enabled: {}, chainId: {}", enabled, chainId);
            return;
        }
        
        log.info("DB 프로파일링 기록 시작 - chainId: {}, elapsedTime: {}s, isPromptDb: {}", chainId, elapsedTime, isPromptDb);
        
        try {
            ProfileData data = profileDataMap.get(chainId);
            if (data != null) {
                if (isPromptDb) {
                    int calls = data.dbPromptCalls.incrementAndGet();
                    long totalTime = data.dbPromptTotalTime.addAndGet((long) (elapsedTime * 1000)); // ms로 변환
                    log.info("DB Prompt 프로파일링 기록 완료 - chainId: {}, calls: {}, totalTime: {}ms", chainId, calls, totalTime);
                } else {
                    int calls = data.dbMainCalls.incrementAndGet();
                    long totalTime = data.dbMainTotalTime.addAndGet((long) (elapsedTime * 1000)); // ms로 변환
                    log.info("DB Main 프로파일링 기록 완료 - chainId: {}, calls: {}, totalTime: {}ms", chainId, calls, totalTime);
                }
            } else {
                log.warn("DB 프로파일링 데이터가 null임 - chainId: {}", chainId);
            }
        } catch (Exception e) {
            log.warn("DB 프로파일링 기록 중 오류: {}", e.getMessage());
        }
    }
    
    /**
     * 프로파일 결과 조회
     */
    public Map<String, Object> getProfile(String chainId) {
        if (!enabled) {
            log.debug("프로파일링이 비활성화되어 있음");
            return new HashMap<>();
        }
        
        ProfileData data = profileDataMap.get(chainId);
        if (data == null) {
            log.warn("프로파일 데이터가 null임 - chainId: {}", chainId);
            return new HashMap<>();
        }
        
        log.info("프로파일 데이터 조회 - chainId: {}, vectorDbCalls: {}, llmCalls: {}, dbMainCalls: {}, dbPromptCalls: {}", 
                chainId, data.vectorDbCalls.get(), data.llmCalls.get(), data.dbMainCalls.get(), data.dbPromptCalls.get());
        
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
        
        log.info("프로파일 결과 생성 완료 - chainId: {}, result: {}", chainId, result);
        return result;
    }
    
    /**
     * 프로파일 데이터 삭제
     */
    public void clearProfile(String chainId) {
        if (!enabled) {
            return;
        }
        
        try {
            profileDataMap.remove(chainId);
            log.debug("프로파일링 데이터 삭제 - chainId: {}", chainId);
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
    }
} 