package com.daquv.agent.quvi.util;

import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.annotation.Order;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import javax.servlet.http.HttpServletRequest;

/**
 * JdbcTemplate의 쿼리 실행을 가로채서 프로파일링을 기록하는 AOP 클래스
 * 성능 최적화: 비동기 프로파일링, 최소 오버헤드
 */
@Aspect
@Component
@Order(1)
public class DatabaseProfilerAspect {

    private static final Logger log = LoggerFactory.getLogger(DatabaseProfilerAspect.class);

    @Autowired
    private RequestProfiler requestProfiler;

    @Autowired
    @Qualifier("mainJdbcTemplate")
    private JdbcTemplate mainJdbcTemplate;

    @Autowired
    @Qualifier("promptJdbcTemplate")
    private JdbcTemplate promptJdbcTemplate;

//    // 프로파일링 활성화 여부 (설정 파일로 제어 가능)
//    private final boolean enabled;

    private static final ThreadLocal<String> chainIdThreadLocal = new ThreadLocal<>();

    /**
     * 모든 JdbcTemplate 메서드 호출 인터셉트 - 인스턴스로 구분
     */
    @Around("execution(* org.springframework.jdbc.core.JdbcTemplate.*(..))")
    public Object profileJdbcTemplateCall(ProceedingJoinPoint joinPoint) throws Throwable {
        String chainId = getChainId();
        if (chainId == null) {
            return joinPoint.proceed();
        }

        Object target = joinPoint.getTarget();
        boolean isPromptDb = (target == promptJdbcTemplate);
        String dbType = isPromptDb ? "promptJdbcTemplate" : "mainJdbcTemplate";

        return executeWithProfiling(joinPoint, chainId, isPromptDb, "JdbcTemplate(" + dbType + ")");
    }

    /**
     * Repository 메서드 호출 인터셉트 - 패키지로 구분
     */
    @Around("execution(* com.daquv.agent.quvi.repository..*(..))")
    public Object profilePromptRepositoryCall(ProceedingJoinPoint joinPoint) throws Throwable {
        String chainId = getChainId();
        if (chainId == null) {
            return joinPoint.proceed();
        }

        String nodeId = determineNodeIdFromStackTrace();
        return executeWithProfiling(joinPoint, chainId, true, "Repository(" + nodeId + ")");
    }

    @Around("execution(* com.daquv.agent.repository..*(..))")
    public Object profileMainRepositoryCall(ProceedingJoinPoint joinPoint) throws Throwable {
        String chainId = getChainId();
        if (chainId == null) {
            return joinPoint.proceed();
        }

        String nodeId = determineNodeIdFromStackTrace();
        return executeWithProfiling(joinPoint, chainId, false, "Repository(" + nodeId + ")");
    }

    /**
     * Service 클래스의 save 관련 메서드들 - 패키지로 구분하여 prompt DB로 분류
     */
    @Around("execution(* com.daquv.agent.quvi.llmadmin..*Service.*(..)) && " +
            "(execution(* *.save*(..)) || execution(* *.create*(..)) || execution(* *.update*(..)) || execution(* *.record*(..)) || execution(* *.complete*(..)))")
    public Object profilePromptServiceCall(ProceedingJoinPoint joinPoint) throws Throwable {
        String chainId = getChainId();
        if (chainId == null) {
            return joinPoint.proceed();
        }

        String nodeId = determineNodeIdFromStackTrace();
        return executeWithProfiling(joinPoint, chainId, true, nodeId);
    }

    private Object executeWithProfiling(ProceedingJoinPoint joinPoint, String chainId,
                                        boolean isPromptDb, String nodeId) throws Throwable {
        long startTime = System.currentTimeMillis();

        try {
            Object result = joinPoint.proceed();

            long endTime = System.currentTimeMillis();
            double elapsedTime = (endTime - startTime) / 1000.0;

            // 프로파일링 기록 - nodeId 포함
            requestProfiler.recordDbCall(chainId, elapsedTime, isPromptDb, nodeId);

            return result;

        } catch (Throwable e) {
            long endTime = System.currentTimeMillis();
            double elapsedTime = (endTime - startTime) / 1000.0;

            // 에러가 발생해도 프로파일링은 기록
            requestProfiler.recordDbCall(chainId, elapsedTime, isPromptDb, nodeId);

            throw e;
        }
    }

    private String getChainId() {
        // 1. ThreadLocal에서 먼저 확인
        String chainId = chainIdThreadLocal.get();
        if (chainId != null) {
            return chainId;
        }

        // 2. RequestAttributes에서 확인
        try {
            RequestAttributes requestAttributes = RequestContextHolder.getRequestAttributes();
            if (requestAttributes instanceof ServletRequestAttributes) {
                HttpServletRequest request = ((ServletRequestAttributes) requestAttributes).getRequest();

                // Request Attribute에서 chainId 확인
                Object chainIdAttr = request.getAttribute("chainId");
                if (chainIdAttr != null) {
                    return chainIdAttr.toString();
                }

                // X-Chain-Id 헤더에서 확인
                Object xChainIdAttr = request.getAttribute("X-Chain-Id");
                if (xChainIdAttr != null) {
                    return xChainIdAttr.toString();
                }
            }
        } catch (Exception e) {
            log.debug("RequestAttributes에서 chainId 획득 실패: {}", e.getMessage());
        }

        return null;
    }

    public static void setChainId(String chainId) {
        chainIdThreadLocal.set(chainId);
        log.debug("ThreadLocal에 chainId 설정: {}", chainId);
    }

    public static void clearChainId() {
        chainIdThreadLocal.remove();
        log.debug("ThreadLocal chainId 정리 완료");
    }

    /**
     * 스택 트레이스에서 워크플로우 노드 ID 결정
     */
    private String determineNodeIdFromStackTrace() {
        StackTraceElement[] stackTrace = Thread.currentThread().getStackTrace();

        for (StackTraceElement element : stackTrace) {
            String className = element.getClassName();

            // 워크플로우 노드들 우선 체크
            if (className.contains("CheckpointNode")) return "checkpoint";
            if (className.contains("CommanderNode")) return "commander";
            if (className.contains("Nl2sqlNode")) return "nl2sql";
            if (className.contains("QueryExecutorNode")) return "executor";
            if (className.contains("SafeguardNode")) return "safeguard";
            if (className.contains("RespondentNode")) return "respondent";
            if (className.contains("NodataNode")) return "nodata";
            if (className.contains("KilljoyNode")) return "killjoy";
            if (className.contains("NextPageNode")) return "next_page";

            // 서비스들
            if (className.contains("QnaService")) return "qna_service";
            if (className.contains("TraceService")) return "trace_service";
            if (className.contains("StateService")) return "state_service";
            if (className.contains("ChainService")) return "chain_service";
            if (className.contains("ConversationService")) return "conversation_service";
            if (className.contains("HistoryService")) return "history_service";

            // 기타
            if (className.contains("QuviController")) return "controller";
            if (className.contains("PromptBuilder")) return "prompt_builder";
        }

        return "system";
    }

}