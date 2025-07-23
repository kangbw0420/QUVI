package com.daquv.agent.workflow.tooluse;

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
public class ToolUseWorkflowExecutionContext {

    @Autowired
    private ChainStateManager stateManager;

    @Autowired
    private ApplicationContext applicationContext;

    @Autowired
    private NodeService nodeService;

    @Autowired
    private StateService stateService;

    /**
     * ToolUse 워크플로우 실행
     * - NextPage 처리
     * - API 경로: funk -> params -> (yqmd or executor) -> respondent
     */
    public void executeToolUseWorkflow(String workflowId) {
        WorkflowState state = stateManager.getState(workflowId);
        if (state == null) {
            throw new IllegalStateException("Workflow ID에 해당하는 State를 찾을 수 없습니다: " + workflowId);
        }

        log.info("=== ToolUse 워크플로우 실행 시작 - workflowId: {} ===", workflowId);

        try {
            // 0. NextPage 처리 (next_page 요청인 경우)
            executeNode("nextPageNode", state);

            if ("next_page".equals(state.getUserQuestion())) {
                log.info("next_page 처리 완료 - ToolUse 워크플로우 종료");
                return;
            }

            // 1. Funk Node - API 함수 선택
            executeNode("funkNode", state);

            if (state.getSelectedApi() == null || state.getSelectedApi().trim().isEmpty()) {
                log.error("API 함수 선택에 실패했습니다.");
                state.setQueryResultStatus("failed");
                state.setSqlError("API 함수 선택에 실패했습니다.");
                return;
            }

            // 2. Params Node - API 파라미터 추출
            executeNode("paramsNode", state);

            // params 조건부 엣지 - 잘못된 날짜인 경우 종료
            if (state.getInvalidDate() != null && state.getInvalidDate()) {
                log.info("invalid_date 감지 - ToolUse 워크플로우 종료");
                return;
            }

            // 3. YQMD Node (aicfo_get_financial_flow API인 경우에만)
            if ("aicfo_get_financial_flow".equals(state.getSelectedApi())) {
                executeNode("yqmdNode", state);

                // YQMD 후 invalid_date 재확인
                if (state.getInvalidDate() != null && state.getInvalidDate()) {
                    log.info("YQMD 후 invalid_date 감지 - ToolUse 워크플로우 종료");
                    return;
                }
            }

            // 4. ToolUse Executor - API 실행
            executeNode("toolUseExecutorNode", state);

            // executor 조건부 엣지
            if (state.getInvalidDate() != null && state.getInvalidDate()) {
                log.info("executor에서 invalid_date 감지 - ToolUse 워크플로우 종료");
                return;
            }

            if (state.getNoData() != null && state.getNoData()) {
                // NoData인 경우 별도 처리 (필요시 nodataNode 호출)
                executeNode("nodataNode", state);
                log.info("nodata 처리 완료 - ToolUse 워크플로우 종료");
                return;
            }

            // 5. ToolUse Respondent - 최종 응답 생성
            if ("success".equals(state.getQueryResultStatus())) {
                executeNode("toolUseRespondentNode", state);
                log.info("ToolUse respondent 처리 완료 - 워크플로우 종료");
            } else {
                log.warn("쿼리 실행이 성공하지 않아 응답 생성을 건너뜁니다. status: {}", state.getQueryResultStatus());
            }

            // 변경된 State 저장
            stateManager.updateState(workflowId, state);

            log.info("=== ToolUse 워크플로우 실행 완료 - workflowId: {} ===", workflowId);

        } catch (Exception e) {
            log.error("ToolUse 워크플로우 실행 실패 - workflowId: {}", workflowId, e);

            state.setQueryResultStatus("failed");
            state.setSqlError("ToolUse Workflow 실행 실패: " + e.getMessage());
            state.setQueryError(true);
            state.setFinalAnswer("ToolUse 처리 중 오류가 발생했습니다.");

            stateManager.updateState(workflowId, state);
            throw e;
        }
    }

    /**
     * 개별 노드 실행 (State 직접 주입 + Trace/State 처리)
     */
    public void executeNode(String nodeBeanName, WorkflowState state) {
        String nodeId = null;

        log.info("ToolUse node executing: {} - state: {}", nodeBeanName, state.getWorkflowId());

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

                log.debug("ToolUse 노드 {} 실행 완료 - traceId: {}", nodeBeanName, nodeId);

            } else {
                throw new IllegalArgumentException("지원하지 않는 ToolUse 노드 타입: " + nodeBeanName);
            }

        } catch (Exception e) {
            log.error("ToolUse 노드 실행 실패: {} - chainId: {}", nodeBeanName, state.getWorkflowId(), e);

            // Trace 오류 상태로 변경
            if (nodeId != null) {
                try {
                    nodeService.markTraceError(nodeId);
                } catch (Exception traceError) {
                    log.error("ToolUse Trace 오류 기록 실패: {}", traceError.getMessage());
                }
            }

            throw e;
        }
    }

    /**
     * ToolUse State를 DB에 저장
     */
    private void saveStateToDatabase(String traceId, WorkflowState state) {
        try {
            java.util.Map<String, Object> stateMap = new java.util.HashMap<>();

            // ToolUse 워크플로우에서 중요한 필드들을 Map으로 변환
            if (state.getUserQuestion() != null) {
                stateMap.put("userQuestion", state.getUserQuestion());
            }
            if (state.getSelectedApi() != null) {
                stateMap.put("selectedApi", state.getSelectedApi());
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
            if (state.getUserInfo() != null && state.getUserInfo().getCompanyId() != null) {
                stateMap.put("companyId", state.getUserInfo().getCompanyId());
            }

            // ToolUse 관련 Boolean 플래그들
            stateMap.put("isApi", state.getIsApi());
            stateMap.put("noData", state.getNoData());
            stateMap.put("futureDate", state.getFutureDate());
            stateMap.put("invalidDate", state.getInvalidDate());
            stateMap.put("queryError", state.getQueryError());
            stateMap.put("hasNext", state.getHasNext());

            // StateService를 통해 DB에 저장
            stateService.updateState(traceId, stateMap);

            try {
                ObjectMapper objectMapper = new ObjectMapper();
                String stateJson = objectMapper.writeValueAsString(stateMap);

                // NodeService를 통해 nodeStateJson 업데이트
                nodeService.updateNodeStateJson(traceId, stateJson);

                log.debug("ToolUse Node state JSON 저장 완료 - traceId: {}", traceId);
            } catch (Exception jsonException) {
                log.error("ToolUse JSON 변환 실패 - traceId: {}", traceId, jsonException);
            }

        } catch (Exception e) {
            log.error("ToolUse State DB 저장 실패 - traceId: {}", traceId, e);
            // State 저장 실패는 워크플로우를 중단하지 않음
        }
    }
}