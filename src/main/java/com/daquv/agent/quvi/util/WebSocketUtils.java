package com.daquv.agent.quvi.util;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

@Component
@Slf4j
public class WebSocketUtils {
    
    private final ObjectMapper objectMapper;
    
    public WebSocketUtils(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }
    
    /**
     * WebSocket 메시지를 전송하는 유틸리티 메서드
     * 
     * @param session WebSocket 세션 (null이면 메시지 전송 안 함)
     * @param message 메시지 타입 (필수)
     * @param data 메시지에 포함할 추가 데이터 (선택)
     */
    public void sendMessage(WebSocketSession session, String message, Map<String, Object> data) {
        if (session == null || !session.isOpen()) {
            return;
        }
        
        try {
            Map<String, Object> messageData = new HashMap<>();
            messageData.put("status", "success");
            messageData.put("message", message);
            
            if (data != null) {
                messageData.putAll(data);
            }
            
            String jsonMessage = objectMapper.writeValueAsString(messageData);
            session.sendMessage(new TextMessage(jsonMessage));
            
            log.debug("WebSocket 메시지 전송 완료: {} - {}", message, data);
            
        } catch (IOException e) {
            log.error("WebSocket 메시지 전송 실패: {} - {}", message, e.getMessage(), e);
        }
    }
    
    /**
     * 간단한 메시지 전송 (추가 데이터 없음)
     */
    public void sendMessage(WebSocketSession session, String message) {
        sendMessage(session, message, null);
    }
    
    /**
     * 노드 시작 메시지 전송
     */
    public void sendNodeStart(WebSocketSession session, String nodeType) {
        Map<String, Object> data = new HashMap<>();
        data.put("node_type", nodeType);
        sendMessage(session, nodeType + "_start", data);
    }
    
    /**
     * 노드 완료 메시지 전송
     */
    public void sendNodeEnd(WebSocketSession session, String nodeType, Map<String, Object> data) {
        if (data == null) {
            data = new HashMap<>();
        }
        data.put("node_type", nodeType);
        sendMessage(session, nodeType + "_end", data);
    }
    
    /**
     * 에러 메시지 전송
     */
    public void sendError(WebSocketSession session, String errorMessage) {
        Map<String, Object> data = new HashMap<>();
        data.put("error", errorMessage);
        sendMessage(session, "error", data);
    }
    
    /**
     * 특정 노드의 진행 상황을 WebSocket으로 전송 (기존 호환성)
     * 현재는 로그로만 출력 (나중에 실제 WebSocket 전송 구현)
     */
    public void sendNodeProgress(String chainId, String nodeId, String message, Map<String, Object> data) {
        try {
            Map<String, Object> progressMessage = new HashMap<>();
            progressMessage.put("type", "node_progress");
            progressMessage.put("chain_id", chainId);
            progressMessage.put("node_id", nodeId);
            progressMessage.put("message", message);
            progressMessage.put("data", data);
            progressMessage.put("timestamp", System.currentTimeMillis());
            
            // 현재는 로그로만 출력
            log.info("노드 진행 상황 - chainId: {}, nodeId: {}, message: {}, data: {}", 
                    chainId, nodeId, message, data);
            
        } catch (Exception e) {
            log.error("WebSocket 메시지 전송 실패 - chainId: {}, nodeId: {}", chainId, nodeId, e);
        }
    }

    /**
     * HIL 요청을 클라이언트에 전송
     */
    public void sendHilRequest(WebSocketSession session, String nodeId, Map<String, Object> hilData) {
        if (session == null || !session.isOpen()) {
            log.warn("WebSocket 세션이 null이거나 닫혀있어 HIL 요청을 전송할 수 없습니다.");
            return;
        }

        try {
            Map<String, Object> message = new HashMap<>();
            message.put("type", "hil_request");
            message.put("node_id", nodeId);
            message.put("timestamp", System.currentTimeMillis());
            message.put("data", hilData);

            String jsonMessage = objectMapper.writeValueAsString(message);
            session.sendMessage(new TextMessage(jsonMessage));

            log.info("HIL 요청 전송 완료: nodeId={}, type={}", nodeId, hilData.get("type"));

        } catch (Exception e) {
            log.error("HIL 요청 전송 실패: nodeId={}", nodeId, e);
        }
    }

    /**
     * HIL 응답 수신 확인을 클라이언트에 전송
     */
    public void sendHilResponseReceived(WebSocketSession session, String nodeId, Map<String, Object> responseData) {
        if (session == null || !session.isOpen()) {
            log.warn("WebSocket 세션이 null이거나 닫혀있어 HIL 응답 확인을 전송할 수 없습니다.");
            return;
        }

        try {
            Map<String, Object> message = new HashMap<>();
            message.put("type", "hil_response_received");
            message.put("node_id", nodeId);
            message.put("timestamp", System.currentTimeMillis());
            message.put("data", responseData);

            String jsonMessage = objectMapper.writeValueAsString(message);
            session.sendMessage(new TextMessage(jsonMessage));

            log.info("HIL 응답 수신 확인 전송 완료: nodeId={}", nodeId);

        } catch (Exception e) {
            log.error("HIL 응답 수신 확인 전송 실패: nodeId={}", nodeId, e);
        }
    }
    
    /**
     * NL2SQL 노드 진행 상황 전송
     */
    public void sendNl2sqlProgress(String chainId, String sqlQuery) {
        Map<String, Object> data = new HashMap<>();
        data.put("sql_query", sqlQuery);
        sendNodeProgress(chainId, "nl2sql", "SQL 쿼리 생성 완료", data);
    }
    
    /**
     * QueryExecutor 노드 진행 상황 전송
     */
    public void sendQueryExecutorProgress(String chainId, int resultRows, int resultColumns) {
        Map<String, Object> data = new HashMap<>();
        data.put("result_rows", resultRows);
        data.put("result_columns", resultColumns);
        sendNodeProgress(chainId, "queryExecutor", "쿼리 실행 완료", data);
    }
    
    /**
     * Safeguard 노드 시작 알림
     */
    public void sendSafeguardStart(String chainId) {
        sendNodeProgress(chainId, "safeguard", "쿼리 검증 시작", new HashMap<>());
    }
    
    /**
     * Safeguard 노드 완료 알림
     */
    public void sendSafeguardComplete(String chainId, String correctedSqlQuery) {
        Map<String, Object> data = new HashMap<>();
        data.put("corrected_sql_query", correctedSqlQuery);
        sendNodeProgress(chainId, "safeguard", "쿼리 검증 완료", data);
    }
    
    /**
     * Nodata 노드 시작 알림
     */
    public void sendNodataStart(String chainId) {
        sendNodeProgress(chainId, "nodata", "데이터 없음 응답 생성 시작", new HashMap<>());
    }
    
    /**
     * Killjoy 노드 시작 알림
     */
    public void sendKilljoyStart(String chainId) {
        sendNodeProgress(chainId, "killjoy", "상품권 외 질문 처리 시작", new HashMap<>());
    }
} 