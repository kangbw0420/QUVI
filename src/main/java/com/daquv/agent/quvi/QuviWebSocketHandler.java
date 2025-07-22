package com.daquv.agent.quvi;

import com.daquv.agent.quvi.dto.QuviRequestDto;
import com.daquv.agent.quvi.llmadmin.WorkflowService;
import com.daquv.agent.quvi.llmadmin.SessionService;
import com.daquv.agent.quvi.logging.ChainLogContext;
import com.daquv.agent.quvi.logging.ChainLogManager;
import com.daquv.agent.quvi.dto.LogLevel;
import com.daquv.agent.quvi.requests.VectorRequest;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.workflow.ChainStateManager;
import com.daquv.agent.workflow.WorkflowExecutionContext;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.workflow.dto.UserInfo;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Component
@Slf4j
public class QuviWebSocketHandler extends TextWebSocketHandler {
    
    private final ChainStateManager stateManager;
    private final WorkflowExecutionContext workflowContext;
    private final VectorRequest vectorRequest;
    private final SessionService sessionService;
    private final WorkflowService workflowService;
    private final ChainLogManager chainLogManager;
    private final RequestProfiler requestProfiler;
    private final ObjectMapper objectMapper;

    public QuviWebSocketHandler(ChainStateManager stateManager, WorkflowExecutionContext workflowContext,
                                VectorRequest vectorRequest, SessionService sessionService,
                                WorkflowService workflowService, ChainLogManager chainLogManager,
                                RequestProfiler requestProfiler, ObjectMapper objectMapper) {
        this.stateManager = stateManager;
        this.workflowContext = workflowContext;
        this.vectorRequest = vectorRequest;
        this.sessionService = sessionService;
        this.workflowService = workflowService;
        this.chainLogManager = chainLogManager;
        this.requestProfiler = requestProfiler;
        this.objectMapper = objectMapper;
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        try {
            String payload = message.getPayload();
            log.info("😊 WebSocket Quvi 요청 수신: {}", payload);
            
            QuviRequestDto request = objectMapper.readValue(payload, QuviRequestDto.class);
            
            // WebSocket 처리 로직 실행 (세션 전달)
            Map<String, Object> response = processWebSocketRequest(request, session);
            
            // WebSocket으로 최종 응답 전송
            String responseJson = objectMapper.writeValueAsString(response);
            session.sendMessage(new TextMessage(responseJson));
            
            log.info("WebSocket 응답 전송 완료");
            
        } catch (Exception e) {
            log.error("❌ WebSocket 메시지 처리 중 예외 발생: {}", e.getMessage(), e);
            
            // 에러 응답 전송
            Map<String, Object> errorResponse = buildErrorResponse(e.getMessage());
            try {
                String errorJson = objectMapper.writeValueAsString(errorResponse);
                session.sendMessage(new TextMessage(errorJson));
            } catch (Exception sendError) {
                log.error("에러 응답 전송 실패: {}", sendError.getMessage());
            }
        }
    }

    private Map<String, Object> processWebSocketRequest(QuviRequestDto request, WebSocketSession session) {
        log.info("😊 WebSocket Quvi 요청 처리 시작: {}", request);
        
        String workflowId = null;
        long startTime = System.currentTimeMillis();
        
        try {
            // 1. Conversation 처리
            String conversationId = getOrCreateConversationId(request);
            log.info("💬 세션 ID: {}", conversationId);

            // 2. Chain 생성 (각 요청마다 독립적)
            workflowId = workflowService.createWorkflow(conversationId, request.getUserQuestion());
            log.info("🔗 체인 생성: {}", workflowId);
            
            // 3. 프로파일링 시작
            requestProfiler.startRequest(workflowId);
            
            // 4. 로그 컨텍스트 생성
            ChainLogContext logContext = chainLogManager.createChainLog(workflowId, request.getUserId(), request.getUserQuestion());
            logContext.setConversationId(conversationId);
            logContext.setCompanyId(request.getCompanyId());

            chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.INFO,
                    String.format("😊 WebSocket Quvi 요청 수신 - userId: %s, question: %s",
                            request.getUserId(), request.getUserQuestion()));

            chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.INFO,
                    String.format("🔗 체인 생성 완료: %s, 세션 ID: %s", workflowId, conversationId));

            // 5. 추천 질문 검색
            List<String> recommendList = getRecommendations(request.getUserQuestion(), workflowId);
            
            // 6. State 생성 및 초기화
            WorkflowState state = stateManager.createState(workflowId);
            initializeState(state, request, conversationId, workflowId, session);

            chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.DEBUG,
                    "🔄 워크플로우 상태 초기화 완료");

            // 7. 워크플로우 실행 (깔끔하게!)
            chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.INFO,
                    "🚀 워크플로우 실행 시작");

            try {
                workflowContext.executeWorkflow(workflowId);
                chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.INFO, "✅ 워크플로우 실행 완료");
            } catch (Exception workflowError) {
                chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.ERROR,
                        String.format("❌ 워크플로우 실행 실패: %s", workflowError.getMessage()), workflowError);

                StringWriter sw = new StringWriter();
                PrintWriter pw = new PrintWriter(sw);
                workflowError.printStackTrace(pw);
                chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.ERROR,
                        String.format("Stack Trace:\n%s", sw.toString()));

                throw workflowError;
            }

            // 8. 최종 결과 조회
            WorkflowState finalState = stateManager.getState(workflowId);
            
            // 9. Chain 완료
            workflowService.completeWorkflow(workflowId, finalState.getFinalAnswer());
            
            // 10. 응답 생성
            long totalTime = System.currentTimeMillis() - startTime;
            Map<String, Object> response = buildResponse(conversationId, workflowId, recommendList, totalTime, finalState);
            
            // 11. 정리
            chainLogManager.completeWorkflow(workflowId, true);
            requestProfiler.clearProfile(workflowId);
            stateManager.removeState(workflowId); // 요청 완료 후 즉시 정리
            
            log.info("WebSocket 요청 처리 완료 - {}ms", totalTime);
            return response;
            
        } catch (Exception e) {
            log.error("❌ WebSocket 요청 처리 실패", e);
            
            // 정리
            if (workflowId != null) {
                chainLogManager.completeWorkflow(workflowId, false);
                requestProfiler.clearProfile(workflowId);
                stateManager.removeState(workflowId);
            }
            
            return buildErrorResponse(e.getMessage());
        }
    }
    
    private String getOrCreateConversationId(QuviRequestDto request) {
        String sessionId = request.getSessionId();
        
        if (sessionId != null && !sessionId.isEmpty() && 
            sessionService.checkConversationId(sessionId)) {

            log.debug("기존 세션 ID 사용: {}", sessionId);
            return sessionId;
        } else {
            String newSessionId = sessionService.makeSessionId(request.getUserId());
            log.debug("새 세션 ID 생성: {}", newSessionId);
            return sessionService.makeSessionId(request.getUserId());
        }
    }
    
    private List<String> getRecommendations(String userQuestion, String workflowId) {
        try {
            List<String> recommendList = vectorRequest.getRecommend(userQuestion, 4, workflowId);
            log.info("📚 추천 질문 검색 완료: {}", recommendList);
            chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.INFO,
                    String.format("📚 추천 질문 검색 완료: %d개", recommendList.size()));
            return recommendList;
        } catch (Exception e) {
            log.error("📚 추천 질문 검색 실패: {}", e.getMessage(), e);
            chainLogManager.addLog(workflowId, "WEBSOCKET_HANDLER", LogLevel.ERROR,
                    "📚 벡터 스토어 연결 실패로 추천 질문을 가져올 수 없습니다");
            return new ArrayList<>();
        }
    }
    
    private void initializeState(WorkflowState state, QuviRequestDto request, String sessionId, String workflowId, WebSocketSession session) {
        state.setUserQuestion(request.getUserQuestion());
        state.setUserInfo(UserInfo.builder()
                .userId(request.getUserId())
                .companyId(request.getCompanyId())
                .build());
        state.setWorkflowId(workflowId);
        state.setNodeId("node_" + System.currentTimeMillis());
        
        // 기본값들 설정
        state.setSafeCount(0);
        state.setSelectedTable("DGC_BALANCE_GA");
        state.setFString("");
        
        // Boolean 플래그들 초기화
        state.setQueryError(false);
        state.setIsJoy(false);
        state.setNoData(false);
        state.setFutureDate(false);
        state.setInvalidDate(false);
        state.setQueryChanged(false);
        state.setHasNext(false);
        
        // WebSocket 세션 설정
        state.setWebSocketSession(session);
        log.info("🔄 워크플로우 상태 초기화 완료 - workflowId: {}, sessionId: {}", workflowId, sessionId);
    }
    
    private Map<String, Object> buildResponse(String conversationId, String chainId, 
                                            List<String> recommendList, long totalTime, 
                                            WorkflowState finalState) {
        Map<String, Object> response = new HashMap<>();
        response.put("status", 200);
        response.put("success", true);
        response.put("retCd", 200);
        response.put("message", "WebSocket 질답 성공");
        
        Map<String, Object> body = new HashMap<>();
        body.put("answer", finalState.getFinalAnswer());
        body.put("raw_data", finalState.getQueryResult());
        body.put("session_id", conversationId);
        body.put("chain_id", chainId);
        body.put("recommend", recommendList);
        body.put("is_api", false);
        body.put("sql_query", finalState.getSqlQuery());
        body.put("selected_table", finalState.getSelectedTable());
        body.put("has_next", finalState.getHasNext() != null ? finalState.getHasNext() : false);
        
        // 프로파일링 정보
        Map<String, Object> profile = requestProfiler.getProfile(chainId);
        profile.put("total_time_ms", totalTime);
        body.put("profile", profile);
        
        response.put("body", body);
        return response;
    }
    
    private Map<String, Object> buildErrorResponse(String errorMessage) {
        Map<String, Object> response = new HashMap<>();
        response.put("status", 500);
        response.put("success", false);
        response.put("retCd", 500);
        response.put("message", "WebSocket 질답 실패");
        
        Map<String, Object> body = new HashMap<>();
        body.put("answer", "죄송합니다. 요청을 처리하는 중 오류가 발생했습니다.");
        body.put("error", errorMessage);
        
        response.put("body", body);
        return response;
    }
} 