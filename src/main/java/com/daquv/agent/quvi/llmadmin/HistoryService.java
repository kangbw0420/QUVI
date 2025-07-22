package com.daquv.agent.quvi.llmadmin;

import com.daquv.agent.entity.State;
import com.daquv.agent.quvi.entity.Workflow;
import com.daquv.agent.repository.StateRepository;
import com.daquv.agent.quvi.repository.WorkflowRepository;
import com.daquv.agent.quvi.repository.SessionRepository;
import com.daquv.agent.quvi.repository.NodeRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.persistence.EntityManager;
import javax.persistence.PersistenceContext;
import javax.persistence.Query;
import java.util.*;
import java.util.stream.Collectors;

@Service
@Transactional(readOnly = true)
public class HistoryService {

    private static final Logger log = LoggerFactory.getLogger(HistoryService.class);
    
    private final StateRepository stateRepository;
    private final WorkflowRepository workflowRepository;
    private final SessionRepository sessionRepository;
    private final NodeRepository nodeRepository;
    private final ObjectMapper objectMapper;

    @PersistenceContext
    private EntityManager entityManager;

    public HistoryService(StateRepository stateRepository, WorkflowRepository workflowRepository,
                          SessionRepository sessionRepository, NodeRepository nodeRepository,
                          ObjectMapper objectMapper) {
        this.stateRepository = stateRepository;
        this.workflowRepository = workflowRepository;
        this.sessionRepository = sessionRepository;
        this.nodeRepository = nodeRepository;
        this.objectMapper = objectMapper;
    }

    /**
     * Retrieve conversation history grouped by chain_id.
     * 
     * @param chainId 체인 ID
     * @param stateHistory 조회할 상태 컬럼 목록
     * @param nodeType 노드 타입
     * @param limit 조회할 최대 개수
     * @return 체인별 히스토리 맵
     */
    public Map<String, List<Map<String, Object>>> getHistory(String chainId, List<String> stateHistory, 
                                                             String nodeType, int limit) {
        log.info("getHistory start - chainId: {}, stateHistory: {}, nodeType: {}, limit: {}", 
                chainId, stateHistory, nodeType, limit);
        
        try {
            // conversation_id를 직접 조회하는 쿼리 사용
            String sessionIdQuery  = "SELECT w.session_id FROM workflow w WHERE w.workflow_id = :chainId";
            Query convQuery = entityManager.createNativeQuery(sessionIdQuery);
            convQuery.setParameter("chainId", chainId);
            String sessionId = (String) convQuery.getSingleResult();
            
            // 동적 쿼리 생성 (JSONB 컬럼 제외)
            String selectedColumns = stateHistory.stream()
                    .filter(col -> !col.equals("date_info"))
                    .map(col -> "s." + col)
                    .collect(Collectors.joining(", "));
            
            String queryString =
                    "WITH latest_workflows AS (" +
                    "    SELECT " + selectedColumns + ", w.workflow_id, w.workflow_start " +
                    "    FROM state s " +
                    "    JOIN node n ON s.node_id = n.node_id " +
                    "    JOIN workflow w ON n.workflow_id = w.workflow_id " +
                    "    WHERE w.session_id = :sessionId " +
                    "    AND n.node_name = :nodeType " +
                    "    ORDER BY w.workflow_start DESC " +
                    "    LIMIT :limit " +
                    ") " +
                    "SELECT * " +
                    "FROM latest_workflows " +
                    "ORDER BY workflow_start ASC";
            
            Query query = entityManager.createNativeQuery(queryString);
            query.setParameter("sessionId", sessionId );
            query.setParameter("nodeType", nodeType);
            query.setParameter("limit", limit);
            
            @SuppressWarnings("unchecked")
            List<Object[]> results = query.getResultList();
            
            if (results.isEmpty()) {
                log.warn("No history found for chain_id: {}", chainId);
                return new HashMap<>();
            }
            
            // 결과를 체인별로 그룹화
            Map<String, List<Map<String, Object>>> historyByChain = new HashMap<>();
            
            for (Object[] row : results) {
                Map<String, Object> historyRow = new HashMap<>();
                
                // 컬럼 순서에 맞게 매핑
                for (int i = 0; i < stateHistory.size(); i++) {
                    String columnName = stateHistory.get(i);
                    Object value = row[i];
                    
                    // JSON 필드 파싱
                    if (columnName.equals("query_result") || columnName.equals("date_info")) {
                        value = parseJsonIfNeeded(value);
                    }
                    
                    historyRow.put(columnName, value);
                }
                
                String resultChainId = (String) row[stateHistory.size()]; // chain_id
                
                historyByChain.computeIfAbsent(resultChainId, k -> new ArrayList<>()).add(historyRow);
            }
            
            log.info("Processed history: {}", historyByChain);
            return historyByChain;
            
        } catch (Exception e) {
            log.error("Error in getHistory - chainId: {}, stateHistory: {}, nodeType: {}", 
                     chainId, stateHistory, nodeType, e);
            return new HashMap<>();
        }
    }

    /**
     * Get the nth most recent history for a given chain_id and column.
     * 
     * @param chainId 체인 ID
     * @param column 조회할 컬럼명
     * @param n 위치 (1 = 최신, 2 = 두 번째 최신, 등)
     * @return 지정된 컬럼의 n번째 최신 히스토리 값
     */
    public Object getNthHistory(String chainId, String column, int n) {
        log.info("getNthHistory - chainId: {}, column: {}, n: {}", chainId, column, n);
        
        try {
            // 현재 workflow의 session_id 조회
            Workflow currentWorkflow = workflowRepository.findById(chainId)
                    .orElseThrow(() -> new IllegalArgumentException("Chain not found: " + chainId));
            
            // conversation_id를 직접 조회하는 쿼리 사용
            String sessionId = currentWorkflow.getSession().getSessionId();

            String queryString =
                "SELECT s." + column + " " +
                "FROM state s " +
                "JOIN node n ON s.node_id = n.node_id " +
                "JOIN workflow w ON n.workflow_id = w.workflow_id " +
                "WHERE w.session_id = :sessionId " +
                "AND s." + column + " IS NOT NULL " +
                "ORDER BY s.id DESC " +
                "LIMIT :n";
            
            Query query = entityManager.createNativeQuery(queryString);
            query.setParameter("sessionId", sessionId);
            query.setParameter("n", n);
            
            @SuppressWarnings("unchecked")
            List<Object> results = query.getResultList();
            
            if (results.isEmpty()) {
                log.warn("No history found for chain_id: {}, column: {}", chainId, column);
                return null;
            }
            
            Object result = results.get(n - 1); // Convert to 0-based index
            
            // JSON 필드 파싱
            if (column.equals("query_result") || column.equals("date_info")) {
                result = parseJsonIfNeeded(result);
            }
            
            return result;
            
        } catch (Exception e) {
            log.error("Error in getNthHistory - chainId: {}, column: {}, n: {}", chainId, column, n, e);
            return null;
        }
    }

    /**
     * Get the most recent history for a given chain_id and column.
     * 
     * @param chainId 체인 ID
     * @param column 조회할 컬럼명
     * @return 최신 히스토리 값
     */
    public Object getRecentHistory(String chainId, String column) {
        return getNthHistory(chainId, column, 1);
    }

    /**
     * Get the second most recent history for a given chain_id and column.
     * 
     * @param chainId 체인 ID
     * @param column 조회할 컬럼명
     * @return 두 번째 최신 히스토리 값
     */
    public Object getFormerHistory(String chainId, String column) {
        return getNthHistory(chainId, column, 2);
    }

    /**
     * JSON 문자열을 객체로 파싱 (필요한 경우)
     */
    private Object parseJsonIfNeeded(Object value) {
        if (value == null || !(value instanceof String)) {
            return value;
        }
        
        String jsonString = (String) value;
        if (jsonString.trim().isEmpty()) {
            return value;
        }
        
        try {
            return objectMapper.readValue(jsonString, Object.class);
        } catch (JsonProcessingException e) {
            log.debug("Failed to parse JSON, returning original value: {}", jsonString);
            return value;
        }
    }

    /**
     * 체인 ID로 모든 상태 히스토리 조회
     * 
     * @param chainId 체인 ID
     * @return 상태 목록
     */
    public List<State> getStatesByChainId(String chainId) {
        log.info("getStatesByChainId - chainId: {}", chainId);
        return stateRepository.findByChainId(chainId);
    }

    /**
     * 트레이스 ID로 상태 히스토리 조회
     * 
     * @param traceId 트레이스 ID
     * @return 상태 목록
     */
    public List<State> getStatesByTraceId(String traceId) {
        log.info("getStatesByTraceId - traceId: {}", traceId);
        return stateRepository.findByTraceIdOrderByIdAsc(traceId);
    }
}
