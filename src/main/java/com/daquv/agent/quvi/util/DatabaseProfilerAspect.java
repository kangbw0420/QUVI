package com.daquv.agent.quvi.util;

import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import javax.servlet.http.HttpServletRequest;

/**
 * JdbcTemplate의 쿼리 실행을 가로채서 프로파일링을 기록하는 AOP 클래스
 * 성능 최적화: 비동기 프로파일링, 최소 오버헤드
 */
@Aspect
@Component
public class DatabaseProfilerAspect {

    private static final Logger log = LoggerFactory.getLogger(DatabaseProfilerAspect.class);

    @Autowired
    private RequestProfiler profiler;

    // 프로파일링 활성화 여부 (설정 파일로 제어 가능)
    private final boolean enabled;

    // ThreadLocal을 사용한 chainId 관리
    private static final ThreadLocal<String> chainIdHolder = new ThreadLocal<>();

    public DatabaseProfilerAspect(@Value("${profiling.enabled:false}") boolean profilingEnabled) {
        this.enabled = profilingEnabled;
        if (enabled) {
            log.info("DatabaseProfilerAspect 초기화 - 프로파일링 활성화됨");
        } else {
            log.info("DatabaseProfilerAspect 초기화 - 프로파일링 비활성화됨 (profiling.enabled: {})", profilingEnabled);
        }
    }

    /**
     * chainId를 ThreadLocal에 설정하는 메서드 (외부에서 호출)
     */
    public static void setChainId(String chainId) {
        chainIdHolder.set(chainId);
        LoggerFactory.getLogger(DatabaseProfilerAspect.class).debug("ThreadLocal에 chainId 설정: {} (Thread: {})",
                chainId, Thread.currentThread().getName());
    }

    /**
     * chainId를 ThreadLocal에서 제거하는 메서드
     */
    public static void clearChainId() {
        String chainId = chainIdHolder.get();
        chainIdHolder.remove();
        LoggerFactory.getLogger(DatabaseProfilerAspect.class).debug("ThreadLocal에서 chainId 제거: {} (Thread: {})",
                chainId, Thread.currentThread().getName());
    }

    /**
     * JdbcTemplate의 queryForList 메서드 실행을 가로채서 프로파일링
     */
    @Around("execution(* org.springframework.jdbc.core.JdbcTemplate.queryForList(..)) && bean(mainJdbcTemplate)")
    public Object profileQueryForList(ProceedingJoinPoint joinPoint) throws Throwable {
        return profileDatabaseCall(joinPoint, false);
    }

    /**
     * JdbcTemplate의 queryForObject 메서드 실행을 가로채서 프로파일링
     */
    @Around("execution(* org.springframework.jdbc.core.JdbcTemplate.queryForObject(..)) && bean(mainJdbcTemplate)")
    public Object profileQueryForObject(ProceedingJoinPoint joinPoint) throws Throwable {
        return profileDatabaseCall(joinPoint, false);
    }

    /**
     * JdbcTemplate의 execute 메서드 실행을 가로채서 프로파일링
     */
    @Around("execution(* org.springframework.jdbc.core.JdbcTemplate.execute(..)) && bean(mainJdbcTemplate)")
    public Object profileExecute(ProceedingJoinPoint joinPoint) throws Throwable {
        return profileDatabaseCall(joinPoint, false);
    }

    /**
     * JdbcTemplate의 update 메서드 실행을 가로채서 프로파일링
     */
    @Around("execution(* org.springframework.jdbc.core.JdbcTemplate.update(..)) && bean(mainJdbcTemplate)")
    public Object profileUpdate(ProceedingJoinPoint joinPoint) throws Throwable {
        return profileDatabaseCall(joinPoint, false);
    }

    /**
     * Prompt DB용 JdbcTemplate의 메서드들을 가로채서 프로파일링
     * (promptJdbcTemplate 빈을 사용하는 경우)
     */
    @Around("execution(* org.springframework.jdbc.core.JdbcTemplate.queryForList(..)) && bean(promptJdbcTemplate)")
    public Object profilePromptQueryForList(ProceedingJoinPoint joinPoint) throws Throwable {
        return profileDatabaseCall(joinPoint, true);
    }

    @Around("execution(* org.springframework.jdbc.core.JdbcTemplate.queryForObject(..)) && bean(promptJdbcTemplate)")
    public Object profilePromptQueryForObject(ProceedingJoinPoint joinPoint) throws Throwable {
        return profileDatabaseCall(joinPoint, true);
    }

    @Around("execution(* org.springframework.jdbc.core.JdbcTemplate.execute(..)) && bean(promptJdbcTemplate)")
    public Object profilePromptExecute(ProceedingJoinPoint joinPoint) throws Throwable {
        return profileDatabaseCall(joinPoint, true);
    }

    @Around("execution(* org.springframework.jdbc.core.JdbcTemplate.update(..)) && bean(promptJdbcTemplate)")
    public Object profilePromptUpdate(ProceedingJoinPoint joinPoint) throws Throwable {
        return profileDatabaseCall(joinPoint, true);
    }

    /**
     * 데이터베이스 호출 프로파일링 공통 로직 (최적화됨)
     */
    private Object profileDatabaseCall(ProceedingJoinPoint joinPoint, boolean isPromptDb) throws Throwable {
        // 프로파일링이 비활성화된 경우 최소 오버헤드로 원본 메서드만 실행
        if (!enabled) {
            return joinPoint.proceed();
        }

        // 현재 요청의 chainId 가져오기
        String chainId = getCurrentChainId();
        String currentThread = Thread.currentThread().getName();

        // 디버그 정보 추가
        log.debug("DB 프로파일링 시작 - Thread: {}, isPromptDb: {}, chainId: {}", currentThread, isPromptDb, chainId);

        long startTime = System.currentTimeMillis();

        try {
            // 원본 메서드 실행
            Object result = joinPoint.proceed();

            // 성공 시 프로파일링 기록
            double elapsedTime = (System.currentTimeMillis() - startTime) / 1000.0;

            if (chainId != null) {
                profiler.recordDbCall(chainId, elapsedTime, isPromptDb);
                log.info("DB 호출 완료 - 소요시간: {}s, isPromptDb: {}, chainId: {} (Thread: {})",
                        elapsedTime, isPromptDb, chainId, currentThread);
            } else {
                log.warn("chainId가 null입니다. DB 프로파일링 기록을 건너뜁니다. - 소요시간: {}s, isPromptDb: {} (Thread: {})",
                        elapsedTime, isPromptDb, currentThread);
            }

            return result;

        } catch (Exception e) {
            // 예외 발생 시에도 시간 측정
            double elapsedTime = (System.currentTimeMillis() - startTime) / 1000.0;

            if (chainId != null) {
                profiler.recordDbCall(chainId, elapsedTime, isPromptDb);
                log.debug("DB 호출 실패 - 소요시간: {}s, isPromptDb: {}, chainId: {} (Thread: {}), 오류: {}",
                        elapsedTime, isPromptDb, chainId, currentThread, e.getMessage());
            } else {
                log.warn("chainId가 null입니다. DB 프로파일링 기록을 건너뜁니다. - 소요시간: {}s, isPromptDb: {} (Thread: {}), 오류: {}",
                        elapsedTime, isPromptDb, currentThread, e.getMessage());
            }

            throw e;
        }
    }

    /**
     * 현재 요청의 chainId를 다양한 방식으로 가져오는 메서드
     */
    private String getCurrentChainId() {
        String chainId = null;
        String currentThread = Thread.currentThread().getName();

        // 1. ThreadLocal에서 먼저 확인
        chainId = chainIdHolder.get();
        if (chainId != null) {
            log.debug("✅ ThreadLocal에서 chainId 획득: {} (Thread: {})", chainId, currentThread);
            return chainId;
        }

        // 2. Request Attribute에서 확인
        try {
            ServletRequestAttributes attributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attributes != null) {
                HttpServletRequest request = attributes.getRequest();

                // 여러 가지 attribute 키로 시도
                String[] attributeKeys = {"chainId", "X-Chain-Id", "chain_id"};
                for (String key : attributeKeys) {
                    chainId = (String) request.getAttribute(key);
                    if (chainId != null) {
                        log.debug("✅ Request Attribute '{}'에서 chainId 획득: {} (Thread: {})", key, chainId, currentThread);
                        return chainId;
                    }
                }

                // Request Header에서 확인
                String[] headerKeys = {"X-Chain-Id", "Chain-Id", "chain-id"};
                for (String key : headerKeys) {
                    chainId = request.getHeader(key);
                    if (chainId != null) {
                        log.debug("✅ Request Header '{}'에서 chainId 획득: {} (Thread: {})", key, chainId, currentThread);
                        return chainId;
                    }
                }
            } else {
                log.debug("⚠️ RequestAttributes가 null입니다. (Thread: {})", currentThread);
            }
        } catch (Exception e) {
            log.debug("⚠️ Request에서 chainId 가져오기 실패: {} (Thread: {})", e.getMessage(), currentThread);
        }

        log.debug("❌ chainId를 찾을 수 없습니다. (Thread: {})", currentThread);
        return null;
    }
}