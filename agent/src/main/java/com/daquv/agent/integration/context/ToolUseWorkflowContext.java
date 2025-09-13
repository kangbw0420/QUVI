package com.daquv.agent.integration.context;

import com.daquv.agent.quvi.llmadmin.HistoryService;
import com.daquv.agent.quvi.llmadmin.NodeService;
import com.daquv.agent.quvi.util.WorkflowNode;
import com.daquv.agent.quvi.util.WorkflowStateManager;
import com.daquv.agent.workflow.tooluse.ToolUseWorkflowState;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Component;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;

@Component
@Slf4j
public class ToolUseWorkflowContext {

    @Autowired
    private WorkflowStateManager<ToolUseWorkflowState> stateManager;

    @Autowired
    private ApplicationContext applicationContext;

    @Autowired
    private NodeService nodeService;

    @Autowired
    private HistoryService historyService;

    /**
     * ToolUse 워크플로우 실행
     * - NextPage 처리
     * - API 경로: funk -> params -> (yqmd or executor) -> respondent
     */
    public void executeToolUseWorkflow(ToolUseWorkflowState state) {
        if (state == null) {
            throw new IllegalStateException("State가 null입니다.");
        }
        
        String workflowId = state.getWorkflowId();

        log.info("=== ToolUse 워크플로우 실행 시작 - workflowId: {} ===", workflowId);

        try {

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
            executeNode("toolUseQueryExecutorNode", state);

            // executor 조건부 엣지
            if (state.getInvalidDate() != null && state.getInvalidDate()) {
                log.info("executor에서 invalid_date 감지 - ToolUse 워크플로우 종료");
                return;
            }

            if (state.getNoData() != null && state.getNoData()) {
                // NoData인 경우 별도 처리 (필요시 nodataNode 호출)
                executeNode("toolUseNodataNode", state);
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
    public void executeNode(String nodeBeanName, ToolUseWorkflowState state) {
        String nodeId = null;

        log.info("ToolUse node executing: {} - state: {}", nodeBeanName, state.getWorkflowId());

        try {
            Object nodeBean = applicationContext.getBean(nodeBeanName);

            if (nodeBean instanceof WorkflowNode) {
                @SuppressWarnings("unchecked")
                WorkflowNode<ToolUseWorkflowState> node = (WorkflowNode<ToolUseWorkflowState>) nodeBean;

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
                throw new IllegalArgumentException("지원하지 않는 WorkflowNode 타입: " + nodeBeanName);
            }

        } catch (Exception e) {
            log.error("ToolUse 노드 실행 실패: {} - workflowId: {}", nodeBeanName, state.getWorkflowId(), e);

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
     * State를 DB에 저장
     */
    private void saveStateToDatabase(String nodeId, ToolUseWorkflowState state) {
        try {
            ObjectMapper objectMapper = new ObjectMapper();
            objectMapper.setSerializationInclusion(JsonInclude.Include.NON_NULL);

            @SuppressWarnings("unchecked")
            String stateJson = objectMapper.writeValueAsString(state);

            nodeService.updateNodeStateJson(nodeId, stateJson);

        } catch (Exception e) {
            log.error("State DB 저장 실패 - traceId: {}", nodeId, e);
        }
    }
}