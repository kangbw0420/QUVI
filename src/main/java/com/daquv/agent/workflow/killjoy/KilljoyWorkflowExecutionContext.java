package com.daquv.agent.workflow.killjoy;

import com.daquv.agent.quvi.llmadmin.HistoryService;
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

import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Component
@Slf4j
public class KilljoyWorkflowExecutionContext {

    @Autowired
    private ChainStateManager stateManager;

    @Autowired
    private ApplicationContext applicationContext;

    @Autowired
    private NodeService nodeService;

    @Autowired
    private StateService stateService;

    @Autowired
    private HistoryService historyService;

    /**
     * Killjoy 워크플로우 실행
     * - 단순히 KilljoyNode만 실행
     */
    public void executeKilljoyWorkflow(String workflowId) {
        WorkflowState state = stateManager.getState(workflowId);
        if (state == null) {
            throw new IllegalStateException("Workflow ID에 해당하는 State를 찾을 수 없습니다: " + workflowId);
        }

        log.info("=== Killjoy 워크플로우 실행 시작 - workflowId: {} ===", workflowId);

        try {
            // KilljoyNode 실행
            executeNode("killjoyNode", state);

            // 변경된 State 저장
            stateManager.updateState(workflowId, state);

            log.info("=== Killjoy 워크플로우 실행 완료 - workflowId: {} ===", workflowId);

        } catch (Exception e) {
            log.error("Killjoy 워크플로우 실행 실패 - workflowId: {}", workflowId, e);

            state.setQueryResultStatus("failed");
            state.setSqlError("Killjoy Workflow 실행 실패: " + e.getMessage());
            state.setQueryError(true);
            state.setFinalAnswer("일상 대화 처리 중 오류가 발생했습니다.");

            stateManager.updateState(workflowId, state);
            throw e;
        }
    }

    /**
     * 개별 노드 실행 (State 직접 주입 + Trace/State 처리)
     */
    public void executeNode(String nodeBeanName, WorkflowState state) {
        String nodeId = null;

        log.info("Killjoy node executing: {} - state: {}", nodeBeanName, state.getWorkflowId());

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

                log.debug("Killjoy 노드 {} 실행 완료 - traceId: {}", nodeBeanName, nodeId);

            } else {
                throw new IllegalArgumentException("지원하지 않는 Killjoy 노드 타입: " + nodeBeanName);
            }

        } catch (Exception e) {
            log.error("Killjoy 노드 실행 실패: {} - chainId: {}", nodeBeanName, state.getWorkflowId(), e);

            // Trace 오류 상태로 변경
            if (nodeId != null) {
                try {
                    nodeService.markTraceError(nodeId);
                } catch (Exception traceError) {
                    log.error("Killjoy Trace 오류 기록 실패: {}", traceError.getMessage());
                }
            }

            throw e;
        }
    }

    /**
     * Killjoy State를 DB에 저장
     */
    private void saveStateToDatabase(String traceId, WorkflowState state) {
        try {
            java.util.Map<String, Object> stateMap = new java.util.HashMap<>();

            // 히스토리 조회에 필요한 핵심 필드들만 저장
            if (state.getUserQuestion() != null) {
                stateMap.put("user_question", state.getUserQuestion());
            }
            if (state.getFinalAnswer() != null) {
                stateMap.put("final_answer", state.getFinalAnswer());
            }

            if (!stateMap.isEmpty()) {
                stateService.updateState(traceId, stateMap);
            }

            // Node 엔티티의 nodeStateJson에도 JSON으로 저장
            try {
                ObjectMapper objectMapper = new ObjectMapper();
                String stateJson = objectMapper.writeValueAsString(stateMap);

                // NodeService를 통해 nodeStateJson 업데이트
                nodeService.updateNodeStateJson(traceId, stateJson);

                log.debug("Killjoy Node state JSON 저장 완료 - traceId: {}", traceId);
            } catch (Exception jsonException) {
                log.error("Killjoy JSON 변환 실패 - traceId: {}", traceId, jsonException);
            }

        } catch (Exception e) {
            log.error("Killjoy State DB 저장 실패 - traceId: {}", traceId, e);
            // State 저장 실패는 워크플로우를 중단하지 않음
        }
    }
}