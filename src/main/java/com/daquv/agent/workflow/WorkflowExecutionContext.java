package com.daquv.agent.workflow;

import com.daquv.agent.quvi.llmadmin.StateService;
import com.daquv.agent.quvi.llmadmin.NodeService;
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
    private NodeService nodeService;
    
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
                log.info("next_page 처리 완료 - 워크플로우 종료");
                return;
            }

            // 1. Checkpoint
            executeNode("checkpointNode", state);

            if (state.getIsJoy() != null && state.getIsJoy()) {
                executeNode("killjoyNode", state);
                log.info("killjoy 처리 완료 - 워크플로우 종료");
                return;
            }

            // 2. IsAPI
            executeNode("isApiNode", state);

            // isapi 조건부 엣지
            if (state.getIsApi() != null && state.getIsApi()) {
                // API 경로: funk -> params -> (yqmd or executor)

                // 2-1. Funk
                executeNode("funkNode", state);

                // 2-2. Params
                executeNode("paramsNode", state);

                // params 조건부 엣지
                if (state.getInvalidDate() != null && state.getInvalidDate()) {
                    log.info("invalid_date 감지 - 워크플로우 종료");
                    return;
                }

                if ("aicfo_get_financial_flow".equals(state.getSelectedApi())) {
                    // 2-3. YQMD
                    executeNode("yqmdNode", state);
                }
                // 2-4. Executor

            } else {
                // SQL 경로: commander -> opendue -> (nl2sql or dater) -> nl2sql -> executor

                // 2-1.
                executeNode("commanderNode", state);

                if (state.getSelectedTable() == null || state.getSelectedTable().trim().isEmpty()) {
                    state.setQueryResultStatus("failed");
                    state.setSqlError("테이블 선택에 실패했습니다.");
                    log.error("Commander에서 테이블 선택 실패");
                    return;
                }

                // 2-2. OpenDue
                executeNode("opendueNode", state);

                // opendue 조건부 엣지
                if (state.getIsOpendue() != null && state.getIsOpendue()) {
                    // 2-3a. NL2SQL 직접 (파이썬: "opendue" -> "nl2sql")
                    executeNode("nl2sqlNode", state);
                } else {
                    // 2-3b. Dater -> NL2SQL
                    executeNode("daterNode", state);
                    executeNode("nl2sqlNode", state);
                }
            }

            // 3. QueryExecutor
            if (state.getSqlQuery() != null && !state.getSqlQuery().trim().isEmpty()) {
                executeNode("queryExecutorNode", state);

                // executor 조건부 엣지: 복잡한 조건 분기
                if (state.getInvalidDate() != null && state.getInvalidDate()) {
                    log.info("executor에서 invalid_date 감지 - 워크플로우 종료");
                    return;
                }

                if (state.getNoData() != null && state.getNoData()) {
                    // 3-1. NoData
                    executeNode("nodataNode", state);
                    log.info("nodata 처리 완료 - 워크플로우 종료");
                    return;
                }

                if (state.getQueryError() != null && state.getQueryError() &&
                        (state.getSafeCount() == null || state.getSafeCount() < 2)) {
                    // 3-2. Safeguard
                    executeNode("safeguardNode", state);

                    // safeguard에서 쿼리가 변경되었다면 executor 재실행
                    if (state.getQueryChanged() != null && state.getQueryChanged()) {
                        executeNode("queryExecutorNode", state);

                        // 재실행 후 다시 조건 체크
                        if (state.getInvalidDate() != null && state.getInvalidDate()) {
                            log.info("safeguard 후 executor에서 invalid_date 감지 - 워크플로우 종료");
                            return;
                        }

                        if (state.getNoData() != null && state.getNoData()) {
                            executeNode("nodataNode", state);
                            log.info("safeguard 후 nodata 처리 완료 - 워크플로우 종료");
                            return;
                        }
                    }
                }

                // 3-3. Respondent
                if ("success".equals(state.getQueryResultStatus())) {
                    executeNode("respondentNode", state);
                    log.info("respondent 처리 완료 - 워크플로우 종료");
                }

            } else {
                state.setQueryResultStatus("failed");
                state.setSqlError("SQL 쿼리가 생성되지 않았습니다.");
                log.error("SQL 쿼리 생성 실패");
            }

            // 변경된 State 저장
            stateManager.updateState(chainId, state);

            log.info("=== 워크플로우 실행 완료 - chainId: {} ===", chainId);

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
        String nodeId = null;

        log.info("node: {}", state);
        
        try {
            Object nodeBean = applicationContext.getBean(nodeBeanName);
            
            if (nodeBean instanceof WorkflowNode) {
                WorkflowNode node = (WorkflowNode) nodeBean;
                
                // 1. Node 생성
                nodeId = nodeService.createNode(state.getChainId(), node.getId());
                state.setTraceId(nodeId);
                
                // 2. 노드 실행
                node.execute(state);
                
                // 3. Trace 완료
                nodeService.completeNode(nodeId);
                
                // 4. State DB 저장 (현재 state의 모든 필드를 저장)
                saveStateToDatabase(nodeId, state);
                
                log.debug("노드 {} 실행 완료 - traceId: {}", nodeBeanName, nodeId);
                
            } else {
                throw new IllegalArgumentException("지원하지 않는 노드 타입: " + nodeBeanName);
            }
            
        } catch (Exception e) {
            log.error("노드 실행 실패: {} - chainId: {}", nodeBeanName, state.getChainId(), e);
            
            // Trace 오류 상태로 변경
            if (nodeId != null) {
                try {
                    nodeService.markTraceError(nodeId);
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
            if (state.getUserInfo().getCompanyId() != null) {
                stateMap.put("companyId", state.getUserInfo().getCompanyId());
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
            stateMap.put("selectedApi", state.getSelectedApi());
            
            // StateService를 통해 DB에 저장
            stateService.updateState(traceId, stateMap);
            
        } catch (Exception e) {
            log.error("State DB 저장 실패 - traceId: {}", traceId, e);
            // State 저장 실패는 워크플로우를 중단하지 않음
        }
    }
} 