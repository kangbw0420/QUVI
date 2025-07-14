package com.daquv.agent.quvi;

import com.daquv.agent.quvi.dto.LogLevel;
import com.daquv.agent.quvi.dto.QuviRequestDto;
import com.daquv.agent.quvi.llmadmin.ChainService;
import com.daquv.agent.quvi.llmadmin.ConversationService;
import com.daquv.agent.quvi.logging.ChainLogContext;
import com.daquv.agent.quvi.logging.ChainLogManager;
import com.daquv.agent.quvi.requests.VectorRequest;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.workflow.ChainStateManager;
import com.daquv.agent.workflow.WorkflowExecutionContext;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.workflow.dto.UserInfo;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.*;

@RestController
public class QuviController {

    private static final Logger log = LoggerFactory.getLogger(QuviController.class);

    private final ChainStateManager stateManager;
    private final WorkflowExecutionContext workflowContext;
    private final VectorRequest vectorRequest;
    private final ConversationService conversationService;
    private final ChainService chainService;
    private final ChainLogManager chainLogManager;
    private final RequestProfiler requestProfiler;

    public QuviController(ChainStateManager stateManager, WorkflowExecutionContext workflowContext,
                          VectorRequest vectorRequest, ConversationService conversationService,
                          ChainService chainService, ChainLogManager chainLogManager,
                          RequestProfiler requestProfiler) {
        this.stateManager = stateManager;
        this.workflowContext = workflowContext;
        this.vectorRequest = vectorRequest;
        this.conversationService = conversationService;
        this.chainService = chainService;
        this.chainLogManager = chainLogManager;
        this.requestProfiler = requestProfiler;
    }

    @PostMapping("/process")
    public ResponseEntity<Map<String, Object>> processInput(@RequestBody QuviRequestDto request) {
        log.info("😊 HTTP Quvi 요청 수신: {}", request);

        String chainId = null;
        long startTime = System.currentTimeMillis();

        try {
            // 1. Conversation 처리
            String conversationId = getOrCreateConversationId(request);
            log.info("💬 세션 ID: {}", conversationId);

            // 2. Chain 생성
            chainId = chainService.createChain(conversationId, request.getUserQuestion());
            log.info("🔗 체인 생성 완료: {}", chainId);

            // 3. 프로파일링 시작
            requestProfiler.startRequest(chainId);

            // 4. 로그 컨텍스트 생성
            ChainLogContext logContext = chainLogManager.createChainLog(
                    chainId,
                    request.getUserId(),
                    request.getUserQuestion()
            );
            logContext.setConversationId(conversationId);
            logContext.setCompanyId(request.getCompanyId());

            chainLogManager.addLog(chainId, "CONTROLLER", LogLevel.INFO,
                    String.format("😊 HTTP Quvi 요청 수신 - userId: %s, question: %s",
                            request.getUserId(), request.getUserQuestion()));

            chainLogManager.addLog(chainId, "CONTROLLER", LogLevel.INFO,
                    String.format("🔗 체인 생성 완료: %s, 세션 ID: %s", chainId, conversationId));

            // 5. 추천 질문 검색
            List<String> recommendList = getRecommendations(request.getUserQuestion(), chainId);

            // 6. State 생성 및 초기화 (WebSocket 세션 없이)
            WorkflowState state = stateManager.createState(chainId);
            initializeState(state, request, conversationId, chainId);

            chainLogManager.addLog(chainId, "CONTROLLER", LogLevel.DEBUG,
                    "🔄 워크플로우 상태 초기화 완료");

            // 7. 워크플로우 실행
            chainLogManager.addLog(chainId, "CONTROLLER", LogLevel.INFO,
                    "🚀 워크플로우 실행 시작");

            try {
                workflowContext.executeWorkflow(chainId);
                chainLogManager.addLog(chainId, "CONTROLLER", LogLevel.INFO, "✅ 워크플로우 실행 완료");
            } catch (Exception workflowError) {
                chainLogManager.addLog(chainId, "CONTROLLER", LogLevel.ERROR,
                        String.format("❌ 워크플로우 실행 실패: %s", removeHttpProtocol(workflowError.getMessage())), workflowError);

                StringWriter sw = new StringWriter();
                PrintWriter pw = new PrintWriter(sw);
                workflowError.printStackTrace(pw);
                chainLogManager.addLog(chainId, "CONTROLLER", LogLevel.ERROR,
                        String.format("Stack Trace:\n%s", sw.toString()));

                throw workflowError;
            }

            // 8. 최종 결과 조회
            WorkflowState finalState = stateManager.getState(chainId);

            // 9. Chain 완료
            chainService.completeChain(chainId, finalState.getFinalAnswer());

            // 로그 컨텍스트에 최종 결과 저장
            logContext.setSelectedTable(finalState.getSelectedTable());
            logContext.setSqlQuery(finalState.getSqlQuery());
            logContext.setFinalAnswer(finalState.getFinalAnswer());
            logContext.setUserInfo(finalState.getUserInfo());

            // 10. 응답 생성
            long totalTime = System.currentTimeMillis() - startTime;
            Map<String, Object> response = buildResponse(conversationId, chainId, recommendList, totalTime, finalState);

            // 11. 정리
            chainLogManager.completeChain(chainId, true);
            requestProfiler.clearProfile(chainId);
            stateManager.removeState(chainId); // 요청 완료 후 즉시 정리

            log.info("HTTP Quvi 요청 처리 완료 - 소요시간: {}ms", totalTime);
            return ResponseEntity.ok(response);

        } catch (Exception e) {
            log.error("❌ HTTP Quvi 요청 처리 중 예외 발생: {}", e.getMessage(), e);

            // 정리
            if (chainId != null) {
                chainLogManager.completeChain(chainId, false);
                requestProfiler.clearProfile(chainId);
                stateManager.removeState(chainId);
            }

            Map<String, Object> errorResponse = buildErrorResponse(e.getMessage());
            return ResponseEntity.ok(errorResponse);
        }
    }

    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("Quvi Server is healthy! 🚀");
    }

    /**
     * 세션 ID 확인 또는 새로 생성
     */
    private String getOrCreateConversationId(QuviRequestDto request) {
        String sessionId = request.getSessionId();

        if (sessionId != null && !sessionId.isEmpty() &&
                conversationService.checkConversationId(sessionId)) {

            log.debug("기존 세션 ID 사용: {}", sessionId);
            return sessionId;
        } else {
            String newSessionId = conversationService.makeConversationId(request.getUserId());

            log.debug("새 세션 ID 생성: {}", newSessionId);
            return newSessionId;
        }
    }

    /**
     * 추천 질문 검색
     */
    private List<String> getRecommendations(String userQuestion, String chainId) {
        try {
            List<String> recommendList = vectorRequest.getRecommend(userQuestion, 4, chainId);
            log.info("📚 추천 질문 검색 완료: {}", recommendList);
            chainLogManager.addLog(chainId, "CONTROLLER", LogLevel.INFO,
                    String.format("📚 추천 질문 검색 완료: %d개", recommendList.size()));
            return recommendList;
        } catch (Exception e) {
            log.error("📚 추천 질문 검색 실패: {}", e.getMessage(), e);
            chainLogManager.addLog(chainId, "CONTROLLER", LogLevel.ERROR,
                    "📚 벡터 스토어 연결 실패로 추천 질문을 가져올 수 없습니다");
            return new ArrayList<>();
        }
    }

    /**
     * 워크플로우 상태 초기화 (HTTP용 - WebSocket 세션 없음)
     */
    private void initializeState(WorkflowState state, QuviRequestDto request, String conversationId,
                                 String chainId) {
        state.setUserQuestion(request.getUserQuestion());
        state.setUserInfo(UserInfo.builder()
                .userId(request.getUserId())
                .companyId(request.getCompanyId())
                .useInttId(request.getUseInttId())
                .build());
        state.setChainId(chainId);
        state.setTraceId("trace_" + System.currentTimeMillis());

        // 기본 상태 초기화
        state.setSafeCount(0);
        state.setQueryError(false);
        state.setQueryResultStatus(null);
        state.setSqlError(null);
        state.setSqlQuery(null);
        state.setQueryResult(null);
        state.setFinalAnswer(null);
        state.setSelectedTable(null);
        state.setFString("");

        // 플래그 초기화
        state.setIsJoy(false);
        state.setNoData(false);
        state.setFutureDate(false);
        state.setInvalidDate(false);
        state.setQueryError(false);
        state.setQueryChanged(false);
        state.setHasNext(false);

        log.info("🔄 워크플로우 상태 초기화 완료 - chainId: {}, conversationId: {}", chainId, conversationId);
    }

    /**
     * 성공 응답 생성
     */
    private Map<String, Object> buildResponse(String conversationId, String chainId,
                                              List<String> recommendList, long totalTime,
                                              WorkflowState finalState) {
        Map<String, Object> response = new HashMap<>();

        // 기본 응답
        response.put("status", 200);
        response.put("success", true);
        response.put("retCd", 200);
        response.put("message", "질답 성공");

        // 응답 본문
        Map<String, Object> body = new HashMap<>();

        // 에러 상태 확인
        String finalAnswer = finalState.getFinalAnswer();
        if (finalAnswer == null || finalAnswer.trim().isEmpty()) {
            finalAnswer = "죄송합니다. 요청을 처리하는 중 오류가 발생했습니다.";
        }

        body.put("answer", finalAnswer);
        body.put("raw_data", finalState.getQueryResult());
        body.put("session_id", conversationId);
        body.put("chain_id", chainId);
        body.put("recommend", recommendList);
        body.put("is_api", false);
        body.put("date_info", Arrays.asList(finalState.getStartDate(), finalState.getEndDate()));
        body.put("sql_query", finalState.getSqlQuery());
        body.put("selected_table", finalState.getSelectedTable());
        body.put("has_next", finalState.getHasNext() != null ? finalState.getHasNext() : false);

        // 프로파일링 정보
        Map<String, Object> profile = new HashMap<>();
        if (chainId != null) {
            Map<String, Object> profileData = requestProfiler.getProfile(chainId);

            // vector_db
            Map<String, Object> vectorDbDefault = new HashMap<>();
            vectorDbDefault.put("calls", 0);
            vectorDbDefault.put("total_time_ms", 0);
            vectorDbDefault.put("avg_time_ms", 0.0);
            profile.put("vector_db", profileData.getOrDefault("vector_db", vectorDbDefault));

            // llm
            Map<String, Object> llmDefault = new HashMap<>();
            llmDefault.put("calls", 0);
            llmDefault.put("total_time_ms", 0);
            llmDefault.put("avg_time_ms", 0.0);
            profile.put("llm", profileData.getOrDefault("llm", llmDefault));

            // db_normal (기존 db_main)
            Map<String, Object> dbNormalDefault = new HashMap<>();
            dbNormalDefault.put("calls", 0);
            dbNormalDefault.put("total_time_ms", 0);
            dbNormalDefault.put("avg_time_ms", 0.0);
            profile.put("db_normal", profileData.getOrDefault("db_main", dbNormalDefault));

            // db_prompt
            Map<String, Object> dbPromptDefault = new HashMap<>();
            dbPromptDefault.put("calls", 0);
            dbPromptDefault.put("total_time_ms", 0);
            dbPromptDefault.put("avg_time_ms", 0.0);
            profile.put("db_prompt", profileData.getOrDefault("db_prompt", dbPromptDefault));
        } else {
            // 프로파일링이 비활성화된 경우 기본값 설정
            Map<String, Object> vectorDbDefault = new HashMap<>();
            vectorDbDefault.put("calls", 0);
            vectorDbDefault.put("total_time_ms", 0);
            vectorDbDefault.put("avg_time_ms", 0.0);
            profile.put("vector_db", vectorDbDefault);

            Map<String, Object> llmDefault = new HashMap<>();
            llmDefault.put("calls", 0);
            llmDefault.put("total_time_ms", 0);
            llmDefault.put("avg_time_ms", 0.0);
            profile.put("llm", llmDefault);

            Map<String, Object> dbNormalDefault = new HashMap<>();
            dbNormalDefault.put("calls", 0);
            dbNormalDefault.put("total_time_ms", 0);
            dbNormalDefault.put("avg_time_ms", 0.0);
            profile.put("db_normal", dbNormalDefault);

            Map<String, Object> dbPromptDefault = new HashMap<>();
            dbPromptDefault.put("calls", 0);
            dbPromptDefault.put("total_time_ms", 0);
            dbPromptDefault.put("avg_time_ms", 0.0);
            profile.put("db_prompt", dbPromptDefault);
        }
        profile.put("total_time_ms", totalTime);
        body.put("profile", profile);

        response.put("body", body);

        return response;
    }

    /**
     * 오류 응답 생성
     */
    private Map<String, Object> buildErrorResponse(String errorMessage) {
        Map<String, Object> response = new HashMap<>();
        response.put("status", 500);
        response.put("success", false);
        response.put("retCd", 500);
        response.put("message", "질답 실패");

        Map<String, Object> body = new HashMap<>();
        body.put("answer", "죄송합니다. 요청을 처리하는 중 오류가 발생했습니다.");
        body.put("error", errorMessage);

        response.put("body", body);
        return response;
    }

    private String removeHttpProtocol(String text) {
        if (text == null) {
            return null;
        }

        // "java.lang" 을 "java_lang" 으로 치환
        return text.replaceAll("java\\.lang", "java_lang");
    }
}