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
import java.util.HashSet;
import java.util.Set;

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

    // 중복 호출 방지를 위한 ThreadLocal
    private static final ThreadLocal<Set<String>> processedMethods = new ThreadLocal<>();

    // ChainId 관리를 위한 ThreadLocal
    private static final ThreadLocal<String> chainIdThreadLocal = new ThreadLocal<>();

    /**
     *  Repository pointcut 통합 및 상속 구조 중복 제거
     * 실제 구현체만 인터셉트하고, 상위 인터페이스는 제외
     */
    @Around("execution(* com.daquv.agent.repository..*(..)) || execution(* com.daquv.agent.quvi.repository..*(..))")
    public Object profilePromptRepositoryCall(ProceedingJoinPoint joinPoint) throws Throwable {
        String chainId = getChainId();
        if (chainId == null) {
            return joinPoint.proceed();
        }

        // JPA 프록시 객체의 실제 타겟 클래스 확인
        String actualClassName = getActualClassName(joinPoint);
        String methodKey = generateMethodKey(joinPoint);
        if (isAlreadyProcessed(methodKey)) {
            return joinPoint.proceed(); // 중복 호출 방지
        }

        // StateRepository는 main DB가 아니라 prompt DB 사용
        boolean isPromptDb = true;

        log.debug("Repository 분류 - actualClassName: {}, isPromptDb: {}", actualClassName, isPromptDb);

        String nodeId = determineNodeIdFromStackTrace();
        return executeWithProfiling(joinPoint, chainId, isPromptDb, "Repository(" + nodeId + ")", methodKey);
    }

    /**
     *  JdbcTemplate은 Repository에서 호출되지 않은 경우만 기록
     * Repository -> JdbcTemplate 중복 방지
     */
    @Around("execution(* org.springframework.jdbc.core.JdbcTemplate.*(..))")
    public Object profileJdbcTemplateCall(ProceedingJoinPoint joinPoint) throws Throwable {
        String chainId = getChainId();
        if (chainId == null) {
            return joinPoint.proceed();
        }

        // Repository 호출 스택에 있는지 확인
        if (isCalledFromRepository()) {
            return joinPoint.proceed(); // Repository에서 호출된 경우 기록하지 않음
        }

        String methodKey = generateMethodKey(joinPoint);
        if (isAlreadyProcessed(methodKey)) {
            return joinPoint.proceed();
        }

        Object target = joinPoint.getTarget();
        boolean isPromptDb = (target == promptJdbcTemplate);
        String dbType = isPromptDb ? "promptJdbcTemplate" : "mainJdbcTemplate";

        return executeWithProfiling(joinPoint, chainId, isPromptDb, "JdbcTemplate(" + dbType + ")", methodKey);
    }

    /**
     * Service는 워크플로우 노드에서 호출되지 않은 경우만 기록
     */
    @Around("execution(* com.daquv.agent.quvi.llmadmin..*Service.*(..))")
    public Object profilePromptServiceCall(ProceedingJoinPoint joinPoint) throws Throwable {
        String chainId = getChainId();
        if (chainId == null) {
            return joinPoint.proceed();
        }

        // 워크플로우 노드에서 호출된 경우 기록하지 않음 (노드 레벨에서 이미 기록됨)
        if (isCalledFromRepository() || willCallRepository(joinPoint)) {
            return joinPoint.proceed();
        }

        String methodKey = generateMethodKey(joinPoint);
        if (isAlreadyProcessed(methodKey)) {
            return joinPoint.proceed();
        }

        String nodeId = determineNodeIdFromStackTrace();
        return executeWithProfiling(joinPoint, chainId, true, nodeId, methodKey);
    }

    /**
     *  워크플로우 노드는 최상위 레벨에서만 기록
     */
    @Around("execution(* com.daquv.agent.workflow.node..*Node.*(..))")
    public Object profileWorkflowNodeCall(ProceedingJoinPoint joinPoint) throws Throwable {
        String chainId = getChainId();
        if (chainId == null) {
            return joinPoint.proceed();
        }

        String methodKey = generateMethodKey(joinPoint);
        if (isAlreadyProcessed(methodKey)) {
            return joinPoint.proceed();
        }

        String nodeId = determineNodeIdFromStackTrace();
        return executeWithProfiling(joinPoint, chainId, false, nodeId, methodKey);
    }

    private Object executeWithProfiling(ProceedingJoinPoint joinPoint, String chainId,
                                        boolean isPromptDb, String nodeId, String methodKey) throws Throwable {
        long startTime = System.currentTimeMillis();

        // 처리 중인 메서드로 마킹
        markAsProcessed(methodKey);

        try {
            Object result = joinPoint.proceed();

            long endTime = System.currentTimeMillis();
            double elapsedTime = (endTime - startTime) / 1000.0;

            // 📌 최소 시간 임계값 적용 (너무 짧은 호출은 무시)
            if (elapsedTime >= 0.001) { // 1ms 이상만 기록
                requestProfiler.recordDbCall(chainId, elapsedTime, isPromptDb, nodeId);
            }
            return result;

        } catch (Throwable e) {
            long endTime = System.currentTimeMillis();
            double elapsedTime = (endTime - startTime) / 1000.0;

            if (elapsedTime >= 0.001) {
                requestProfiler.recordDbCall(chainId, elapsedTime, isPromptDb, nodeId);
            }
            throw e;
        } finally {
            // 처리 완료 후 마킹 해제
            unmarkAsProcessed(methodKey);
        }
    }

    /**
     * 📌 유틸리티 메서드들
     */
    private String generateMethodKey(ProceedingJoinPoint joinPoint) {
        // JPA 프록시 객체의 실제 클래스명과 메서드명으로 고유 키 생성
        String actualClassName = getActualClassName(joinPoint);
        return actualClassName + "." + joinPoint.getSignature().getName() + ":" + Thread.currentThread().getId();
    }

    private boolean willCallRepository(ProceedingJoinPoint joinPoint) {
        // Service 메서드가 Repository를 호출할 가능성이 높은 경우
        String methodName = joinPoint.getSignature().getName();
        return methodName.contains("save") || methodName.contains("update") ||
                methodName.contains("delete") || methodName.contains("find");
    }

    private String getActualClassName(ProceedingJoinPoint joinPoint) {
        Object target = joinPoint.getTarget();
        if (target != null) {
            Class<?> targetClass = target.getClass();
            // Spring 프록시 클래스인 경우 실제 타겟 클래스명 추출
            if (targetClass.getName().contains("$")) {
                // CGLIB 프록시: com.daquv.SomeClass$EnhancerBySpringCGLIB$12345
                String className = targetClass.getName();
                if (className.contains("$")) {
                    return className.substring(0, className.indexOf("$"));
                }
            }
            return targetClass.getName();
        }
        return joinPoint.getSignature().getDeclaringTypeName();
    }

    private boolean isAlreadyProcessed(String methodKey) {
        Set<String> processed = processedMethods.get();
        return processed != null && processed.contains(methodKey);
    }

    private void markAsProcessed(String methodKey) {
        Set<String> processed = processedMethods.get();
        if (processed == null) {
            processed = new HashSet<>();
            processedMethods.set(processed);
        }
        processed.add(methodKey);
    }

    private void unmarkAsProcessed(String methodKey) {
        Set<String> processed = processedMethods.get();
        if (processed != null) {
            processed.remove(methodKey);
            if (processed.isEmpty()) {
                processedMethods.remove();
            }
        }
    }

    private boolean isCalledFromRepository() {
        StackTraceElement[] stackTrace = Thread.currentThread().getStackTrace();
        for (StackTraceElement element : stackTrace) {
            String className = element.getClassName();
            if (className.contains("com.daquv.agent.quvi.repository") ||
                    className.contains("com.daquv.agent.repository")) {
                return true;
            }
        }
        return false;
    }

    private boolean isCalledFromWorkflowNode() {
        StackTraceElement[] stackTrace = Thread.currentThread().getStackTrace();
        for (StackTraceElement element : stackTrace) {
            String className = element.getClassName();
            if (className.contains("com.daquv.agent.workflow.node") && className.endsWith("Node")) {
                return true;
            }
        }
        return false;
    }

    private String getChainId() {
        // 1. RequestAttributes에서 chainId 조회 시도
        try {
            RequestAttributes requestAttributes = RequestContextHolder.getRequestAttributes();
            if (requestAttributes instanceof ServletRequestAttributes) {
                HttpServletRequest request = ((ServletRequestAttributes) requestAttributes).getRequest();
                Object chainIdObj = request.getAttribute("chainId");
                if (chainIdObj != null) {
                    return chainIdObj.toString();
                }
            }
        } catch (Exception e) {
            log.debug("RequestAttributes에서 chainId 조회 실패", e);
        }

        // 2. ThreadLocal에서 chainId 조회
        String threadLocalChainId = chainIdThreadLocal.get();
        if (threadLocalChainId != null) {
            return threadLocalChainId;
        }

        return null;
    }

    /**
     * ThreadLocal에 chainId 설정 (외부에서 호출 가능)
     */
    public static void setChainId(String chainId) {
        if (chainId != null) {
            chainIdThreadLocal.set(chainId);
            log.debug("ThreadLocal에 chainId 설정: {}", chainId);
        }
    }

    /**
     * ThreadLocal에서 chainId 제거
     */
    public static void removeChainId() {
        chainIdThreadLocal.remove();
        log.debug("ThreadLocal에서 chainId 제거");
    }

    private String determineNodeIdFromStackTrace() {
        // 기존 로직 유지
        StackTraceElement[] stackTrace = Thread.currentThread().getStackTrace();

        for (StackTraceElement element : stackTrace) {
            String className = element.getClassName();
            String methodName = element.getMethodName();

            if (className.contains("Service")) {
                return extractServiceName(className);
            } else if (className.contains("Node")) {
                return extractNodeName(className);
            } else if (className.contains("Controller")) {
                return "controller";
            }
        }

        return "unknown";
    }

    private String extractServiceName(String className) {
        if (className.contains(".")) {
            String simpleName = className.substring(className.lastIndexOf('.') + 1);
            return simpleName.toLowerCase().replace("service", "_service");
        }
        return "service";
    }

    private String extractNodeName(String className) {
        if (className.contains(".")) {
            String simpleName = className.substring(className.lastIndexOf('.') + 1);
            return simpleName.toLowerCase().replace("node", "");
        }
        return "node";
    }

    // ThreadLocal cleanup을 위한 메서드
    public static void clearThreadLocal() {
        processedMethods.remove();
        chainIdThreadLocal.remove();
        log.debug("ThreadLocal 정리 완료");
    }
}