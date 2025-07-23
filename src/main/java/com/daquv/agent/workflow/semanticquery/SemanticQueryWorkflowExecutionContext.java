package com.daquv.agent.workflow.semanticquery;

import com.daquv.agent.quvi.llmadmin.StateService;
import com.daquv.agent.quvi.llmadmin.NodeService;
import com.daquv.agent.workflow.ChainStateManager;
import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Component;

@Component
@Slf4j
public class SemanticQueryWorkflowExecutionContext {

    @Autowired
    private ChainStateManager stateManager;

    @Autowired
    private ApplicationContext applicationContext;

    @Autowired
    private NodeService nodeService;

    @Autowired
    private StateService stateService;

    /**
     * SemanticQuery 워크플로우 실행
     * - SQL 경로: commander -> opendue -> (nl2sql or dater) -> nl2sql -> executor -> (safeguard or respondent)
     */
    public void executeSemanticQueryWorkflow(String workflowId) {
        WorkflowState state = stateManager.getState(workflowId);
        if (state == null) {
            throw new IllegalStateException("Workflow ID에 해당하는 State를 찾을 수 없습니다: " + workflowId);
        }

        log.info("=== SemanticQuery 워크플로우 실행 시작 - workflowId: {} ===", workflowId);

        try {

            executeNode("nextPageNode", state);

            if ("next_page".equals(state.getUserQuestion())) {
                log.info("next_page 처리 완료 - SemanticQuery 워크플로우 종료");
                return;
            }

            // 1. Commander Node - 테이블 선택
            executeNode("commanderNode", state);

            if (state.getSelectedTable() == null || state.getSelectedTable().trim().isEmpty()) {
                log.error("SemanticQuery: Commander에서 테이블 선택 실패");
                state.setQueryResultStatus("failed");
                state.setSqlError("테이블 선택에 실패했습니다.");
                return;
            }

            // 2. OpenDue Node - 개설일/만기일 분류
            executeNode("opendueNode", state);

            // opendue 조건부 엣지
            if (state.getIsOpendue() != null && state.getIsOpendue()) {
                // 2-1a. NL2SQL 직접 실행 (개설일/만기일인 경우)
                log.info("SemanticQuery: 개설일/만기일 질문으로 분류 - NL2SQL 직접 실행");
                executeNode("nl2sqlNode", state);
            } else {
                // 2-1b. Dater -> NL2SQL (일반적인 경우)
                log.info("SemanticQuery: 일반 질문으로 분류 - Dater -> NL2SQL 순서 실행");
                executeNode("daterNode", state);

                // 날짜 추출 실패 시 종료
                if (state.getStartDate() == null || state.getEndDate() == null) {
                    log.error("SemanticQuery: 날짜 정보 추출에 실패했습니다.");
                    state.setQueryResultStatus("failed");
                    state.setSqlError("날짜 정보 추출에 실패했습니다.");
                    return;
                }

                executeNode("nl2sqlNode", state);
            }

            // SQL 쿼리 생성 실패 시 종료
            if (state.getSqlQuery() == null || state.getSqlQuery().trim().isEmpty()) {
                log.error("SemanticQuery: SQL 쿼리 생성에 실패했습니다.");
                state.setQueryResultStatus("failed");
                state.setSqlError("SQL 쿼리 생성에 실패했습니다.");
                return;
            }

            // 3. SemanticQuery Executor - SQL 실행
            executeNode("semanticQueryExecutorNode", state);

            // executor 조건부 엣지
            if (state.getInvalidDate() != null && state.getInvalidDate()) {
                log.info("SemanticQuery: executor에서 invalid_date 감지 - 워크플로우 종료");
                return;
            }

            if (state.getNoData() != null && state.getNoData()) {
                // 3-1. NoData 처리
                executeNode("nodataNode", state);
                log.info("SemanticQuery: nodata 처리 완료 - 워크플로우 종료");
                return;
            }

            if (state.getQueryError() != null && state.getQueryError() &&
                    (state.getSafeCount() == null || state.getSafeCount() < 2)) {
                // 3-2. Safeguard - 쿼리 오류 수정
                executeNode("safeguardNode", state);

                // safeguard에서 쿼리가 변경되었다면 executor 재실행
                if (state.getQueryChanged() != null && state.getQueryChanged()) {
                    log.info("SemanticQuery: Safeguard에서 쿼리 수정됨 - Executor 재실행");
                    executeNode("semanticQueryExecutorNode", state);

                    // 재실행 후 다시 조건 체크
                    if (state.getInvalidDate() != null && state.getInvalidDate()) {
                        log.info("SemanticQuery: safeguard 후 executor에서 invalid_date 감지 - 워크플로우 종료");
                        return;
                    }

                    if (state.getNoData() != null && state.getNoData()) {
                        executeNode("nodataNode", state);
                        log.info("SemanticQuery: safeguard 후 nodata 처리 완료 - 워크플로우 종료");
                        return;
                    }
                }
            }

            // 4. SemanticQuery Respondent - 최종 응답 생성
            if ("success".equals(state.getQueryResultStatus())) {
                executeNode("semanticQueryRespondentNode", state);
                log.info("SemanticQuery: respondent 처리 완료 - 워크플로우 종료");
            } else {
                log.warn("SemanticQuery: 쿼리 실행이 성공하지 않아 응답 생성을 건너뜁니다. status: {}", state.getQueryResultStatus());
            }

            // 변경된 State 저장
            stateManager.updateState(workflowId, state);

            log.info("=== SemanticQuery 워크플로우 실행 완료 - workflowId: {} ===", workflowId);

        } catch (Exception e) {
            log.error("SemanticQuery 워크플로우 실행 실패 - workflowId: {}", workflowId, e);

            state.setQueryResultStatus("failed");
            state.setSqlError("SemanticQuery Workflow 실행 실패: " + e.getMessage());
            state.setQueryError(true);
            state.setFinalAnswer("SemanticQuery 처리 중 오류가 발생했습니다.");

            stateManager.updateState(workflowId, state);
            throw e;
        }
    }

    /**
     * 개별 노드 실행 (State 직접 주입 + Trace/State 처리)
     */
    public void executeNode(String nodeBeanName, WorkflowState state) {
        String nodeId = null;

        log.info("SemanticQuery node executing: {} - state: {}", nodeBeanName, state.getWorkflowId());

        try {
            Object nodeBean = applicationContext.getBean(nodeBeanName);

            if (nodeBean instanceof WorkflowNode) {
                WorkflowNode node = (WorkflowNode) nodeBean;

                // 1. Node 생성
                nodeId = nodeService.createNode(state.getWorkflowId(), node.getId());
                state.setNodeId(nodeId);

                // 2. 노드 실행
                node.execute(state);

                // 3. Trace 완료
                nodeService.completeNode(nodeId);

                // 4. State DB 저장 (현재 state의 모든 필드를 저장)
                saveStateToDatabase(nodeId, state);

                log.debug("SemanticQuery 노드 {} 실행 완료 - traceId: {}", nodeBeanName, nodeId);

            } else {
                throw new IllegalArgumentException("지원하지 않는 SemanticQuery 노드 타입: " + nodeBeanName);
            }

        } catch (Exception e) {
            log.error("SemanticQuery 노드 실행 실패: {} - chainId: {}", nodeBeanName, state.getWorkflowId(), e);

            // Trace 오류 상태로 변경
            if (nodeId != null) {
                try {
                    nodeService.markTraceError(nodeId);
                } catch (Exception traceError) {
                    log.error("SemanticQuery Trace 오류 기록 실패: {}", traceError.getMessage());
                }
            }

            throw e;
        }
    }

    /**
     * SemanticQuery State를 DB에 저장
     */
    private void saveStateToDatabase(String traceId, WorkflowState state) {
        try {
            java.util.Map<String, Object> stateMap = new java.util.HashMap<>();

            // SemanticQuery 워크플로우에서 중요한 필드들을 Map으로 변환 (빈 값이 아닐 때만)
            if (state.getUserQuestion() != null && !state.getUserQuestion().trim().isEmpty()) {
                stateMap.put("user_question", state.getUserQuestion());
            }
            if (state.getSelectedTable() != null && !state.getSelectedTable().trim().isEmpty()) {
                stateMap.put("selected_table", state.getSelectedTable());
            }
            if (state.getSqlQuery() != null && !state.getSqlQuery().trim().isEmpty()) {
                stateMap.put("sql_query", state.getSqlQuery());
            }
            if (state.getQueryResult() != null && !state.getQueryResult().isEmpty()) {
                stateMap.put("query_result", state.getQueryResult());
            }
            if (state.getFinalAnswer() != null && !state.getFinalAnswer().trim().isEmpty()) {
                stateMap.put("final_answer", state.getFinalAnswer());
            }
            if (state.getTablePipe() != null && !state.getTablePipe().trim().isEmpty()) {
                stateMap.put("table_pipe", state.getTablePipe());
            }
            if (state.getFString() != null && !state.getFString().trim().isEmpty()) {
                stateMap.put("fstring_answer", state.getFString());
            }

            // 날짜 정보 (배열 형태로) - 둘 다 null이 아니고 빈 문자열이 아닐 때만
            if (state.getStartDate() != null && !state.getStartDate().trim().isEmpty() &&
                    state.getEndDate() != null && !state.getEndDate().trim().isEmpty()) {
                java.util.List<String> dateInfo = new java.util.ArrayList<>();
                dateInfo.add(state.getStartDate());
                dateInfo.add(state.getEndDate());
                stateMap.put("date_info", dateInfo);
            }


            // StateService를 통해 기존 State 테이블에도 저장 (빈 맵이 아닐 때만)
            if (!stateMap.isEmpty()) {
                stateService.updateState(traceId, stateMap);
            }

            // Node 엔티티의 nodeStateJson에도 JSON으로 저장
            try {
                com.fasterxml.jackson.databind.ObjectMapper objectMapper = new com.fasterxml.jackson.databind.ObjectMapper();
                String stateJson = objectMapper.writeValueAsString(stateMap);

                // NodeService를 통해 nodeStateJson 업데이트
                nodeService.updateNodeStateJson(traceId, stateJson);

                log.debug("SemanticQuery Node state JSON 저장 완료 - traceId: {}", traceId);
            } catch (Exception jsonException) {
                log.error("SemanticQuery JSON 변환 실패 - traceId: {}", traceId, jsonException);
            }

        } catch (Exception e) {
            log.error("SemanticQuery State DB 저장 실패 - traceId: {}", traceId, e);
            // State 저장 실패는 워크플로우를 중단하지 않음
        }
    }
}