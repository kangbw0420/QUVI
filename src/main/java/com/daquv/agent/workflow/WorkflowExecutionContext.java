package com.daquv.agent.workflow;

import com.daquv.agent.quvi.llmadmin.StateService;
import com.daquv.agent.quvi.llmadmin.TraceService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Component;

@Component
@Slf4j
public class WorkflowExecutionContext {
    
    @Autowired
    private ChainStateManager stateManager;
    
    @Autowired
    private ApplicationContext applicationContext;
    
    @Autowired
    private TraceService traceService;
    
    @Autowired
    private StateService stateService;
    
    /**
     * 워크플로우 실행 (State를 노드들에게 직접 전달)
     */
    public void executeWorkflow(String chainId) {
        WorkflowState state = stateManager.getState(chainId);
        if (state == null) {
            throw new IllegalStateException("Chain ID에 해당하는 State를 찾을 수 없습니다: " + chainId);
        }
        
        log.info("=== 워크플로우 실행 시작 - chainId: {} ===", chainId);
        
        try {
            // 0. NextPage 처리
            executeNode("nextPageNode", state);
            if ("next_page".equals(state.getUserQuestion())) {
                return;
            }
            
            // 1. Checkpoint
            executeNode("checkpointNode", state);
            if (state.getIsJoy() != null && state.getIsJoy()) {
                executeNode("killjoyNode", state);
                return;
            }

            // 2. Commander or Funk 로직
            if (state.getIsApi() != null && state.getIsApi()) {
                executeNode("funkNode",  state);
                // params, yqmd 등 추가 필요
            } else {
                executeNode("commanderNode", state);
                if (state.getSelectedTable() == null || state.getSelectedTable().trim().isEmpty()) {
                    state.setQueryResultStatus("failed");
                    state.setSqlError("테이블 선택에 실패했습니다.");
                    return;
                }
                // 3. NL2SQL
                executeNode("nl2sqlNode", state);
            }
            
            // 4. QueryExecutor
            if (state.getSqlQuery() != null && !state.getSqlQuery().trim().isEmpty()) {
                executeNode("queryExecutorNode", state);
                
                // 4-1. Safeguard
                if (state.getQueryError() != null && state.getQueryError() && 
                    state.getSafeCount() != null && state.getSafeCount() < 2) {
                    executeNode("safeguardNode", state);
                    
                    if (state.getQueryChanged() != null && state.getQueryChanged()) {
                        executeNode("queryExecutorNode", state);
                    }
                }
            } else {
                state.setQueryResultStatus("failed");
                state.setSqlError("SQL 쿼리가 생성되지 않았습니다.");
            }
            
            // 5. Response 생성
            if ("success".equals(state.getQueryResultStatus())) {
                if (state.getNoData() != null && state.getNoData()) {
                    executeNode("nodataNode", state);
                } else {
                    executeNode("respondentNode", state);
                }
            }
            
            // 변경된 State 저장
            stateManager.updateState(chainId, state);
            
        } catch (Exception e) {
            log.error("워크플로우 실행 실패 - chainId: {}", chainId, e);
            
            state.setQueryResultStatus("failed");
            state.setSqlError("Workflow 실행 실패: " + e.getMessage());
            state.setQueryError(true);
            state.setFinalAnswer("처리 중 오류가 발생했습니다.");
            
            stateManager.updateState(chainId, state);
            throw e;
        }
    }
    
    /**
     * 개별 노드 실행 (State 직접 주입 + Trace/State 처리)
     */
    private void executeNode(String nodeBeanName, WorkflowState state) {
        String traceId = null;
        
        try {
            Object nodeBean = applicationContext.getBean(nodeBeanName);
            
            if (nodeBean instanceof WorkflowNode) {
                WorkflowNode node = (WorkflowNode) nodeBean;
                
                // 1. Trace 생성
                traceId = traceService.createTrace(state.getChainId(), node.getId());
                state.setTraceId(traceId);
                
                // 2. 노드 실행
                node.execute(state);
                
                // 3. Trace 완료
                traceService.completeTrace(traceId);
                
                // 4. State DB 저장 (현재 state의 모든 필드를 저장)
                saveStateToDatabase(traceId, state);
                
                log.debug("노드 {} 실행 완료 - traceId: {}", nodeBeanName, traceId);
                
            } else {
                throw new IllegalArgumentException("지원하지 않는 노드 타입: " + nodeBeanName);
            }
            
        } catch (Exception e) {
            log.error("노드 실행 실패: {} - chainId: {}", nodeBeanName, state.getChainId(), e);
            
            // Trace 오류 상태로 변경
            if (traceId != null) {
                try {
                    traceService.markTraceError(traceId);
                } catch (Exception traceError) {
                    log.error("Trace 오류 기록 실패: {}", traceError.getMessage());
                }
            }
            
            throw e;
        }
    }
    
    /**
     * State를 DB에 저장
     */
    private void saveStateToDatabase(String traceId, WorkflowState state) {
        try {
            java.util.Map<String, Object> stateMap = new java.util.HashMap<>();
            
            // WorkflowState의 모든 필드를 Map으로 변환
            if (state.getUserQuestion() != null) {
                stateMap.put("userQuestion", state.getUserQuestion());
            }
            if (state.getSelectedTable() != null) {
                stateMap.put("selectedTable", state.getSelectedTable());
            }
            if (state.getSqlQuery() != null) {
                stateMap.put("sqlQuery", state.getSqlQuery());
            }
            if (state.getQueryResult() != null) {
                stateMap.put("queryResult", state.getQueryResult());
            }
            if (state.getFinalAnswer() != null) {
                stateMap.put("finalAnswer", state.getFinalAnswer());
            }
            if (state.getSqlError() != null) {
                stateMap.put("sqlError", state.getSqlError());
            }
            if (state.getQueryResultStatus() != null) {
                stateMap.put("queryResultStatus", state.getQueryResultStatus());
            }
            if (state.getTotalRows() != null) {
                stateMap.put("totalRows", state.getTotalRows());
            }
            if (state.getFString() != null) {
                stateMap.put("fString", state.getFString());
            }
            if (state.getTablePipe() != null) {
                stateMap.put("tablePipe", state.getTablePipe());
            }
            if (state.getStartDate() != null) {
                stateMap.put("startDate", state.getStartDate());
            }
            if (state.getEndDate() != null) {
                stateMap.put("endDate", state.getEndDate());
            }
            
            // Boolean 플래그들
            stateMap.put("isJoy", state.getIsJoy());
            stateMap.put("noData", state.getNoData());
            stateMap.put("futureDate", state.getFutureDate());
            stateMap.put("invalidDate", state.getInvalidDate());
            stateMap.put("queryError", state.getQueryError());
            stateMap.put("queryChanged", state.getQueryChanged());
            stateMap.put("hasNext", state.getHasNext());
            stateMap.put("safeCount", state.getSafeCount());
            
            // StateService를 통해 DB에 저장
            stateService.updateState(traceId, stateMap);
            
        } catch (Exception e) {
            log.error("State DB 저장 실패 - traceId: {}", traceId, e);
            // State 저장 실패는 워크플로우를 중단하지 않음
        }
    }
} 