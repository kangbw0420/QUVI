package com.daquv.agent.workflow.tooluse;

import com.daquv.agent.quvi.llmadmin.HistoryService;
import com.daquv.agent.quvi.llmadmin.NodeService;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Component;

@Component
@Slf4j
public class ToolUseWorkflowExecutionContext {

    @Autowired
    private ToolUseStateManager stateManager;

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
    public void executeToolUseWorkflow(String workflowId) {
        ToolUseWorkflowState state = stateManager.getState(workflowId);
        if (state == null) {
            throw new IllegalStateException("Workflow ID에 해당하는 State를 찾을 수 없습니다: " + workflowId);
        }

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
    public void executeNode(String nodeBeanName, ToolUseWorkflowState state) {
        String nodeId = null;

        log.info("ToolUse node executing: {} - state: {}", nodeBeanName, state.getWorkflowId());

        try {
            Object nodeBean = applicationContext.getBean(nodeBeanName);

            if (nodeBean instanceof ToolUseWorkflowNode) {
                ToolUseWorkflowNode node = (ToolUseWorkflowNode) nodeBean;

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
    private void saveStateToDatabase(String traceId, ToolUseWorkflowState state) {
        try {
            java.util.Map<String, Object> stateMap = new java.util.HashMap<>();

            // 히스토리 조회에 필요한 핵심 필드들만 저장 (빈 값이 아닐 때만)
            if (state.getUserQuestion() != null && !state.getUserQuestion().trim().isEmpty()) {
                stateMap.put("userQuestion", state.getUserQuestion());
            }
            if (state.getSelectedApi() != null && !state.getSelectedApi().trim().isEmpty()) {
                stateMap.put("selectedTable", state.getSelectedApi()); // API명을 selected_table에 저장
            }
            if (state.getSqlQuery() != null && !state.getSqlQuery().trim().isEmpty()) {
                stateMap.put("sqlQuery", state.getSqlQuery());
            }
            if (state.getQueryResult() != null && !state.getQueryResult().isEmpty()) {
                stateMap.put("queryResult", state.getQueryResult());
            }
            if (state.getFinalAnswer() != null && !state.getFinalAnswer().trim().isEmpty()) {
                stateMap.put("finalAnswer", state.getFinalAnswer());
            }
            if (state.getSqlError() != null && !state.getSqlError().trim().isEmpty()) {
                stateMap.put("sqlError", state.getSqlError());
            }
            if (state.getQueryResultStatus() != null && !state.getQueryResultStatus().trim().isEmpty()) {
                stateMap.put("queryResultStatus", state.getQueryResultStatus());
            }
            if (state.getTablePipe() != null && !state.getTablePipe().trim().isEmpty()) {
                stateMap.put("tablePipe", state.getTablePipe());
            }
            if (state.getFString() != null && !state.getFString().trim().isEmpty()) {
                stateMap.put("fstringAnswer", state.getFString());
            }
            if (state.getStartDate() != null && !state.getStartDate().trim().isEmpty() &&
                    state.getEndDate() != null && !state.getEndDate().trim().isEmpty()) {
                java.util.List<String> dateInfo = new java.util.ArrayList<>();
                dateInfo.add(state.getStartDate());
                dateInfo.add(state.getEndDate());
                stateMap.put("date_info", dateInfo);
            }
            if (state.getUserInfo().getCompanyId() != null  && !state.getUserInfo().getCompanyId().trim().isEmpty()) {
                stateMap.put("companyId", state.getUserInfo().getCompanyId());
            }


            ObjectMapper objectMapper = new ObjectMapper();
            String stateJson = objectMapper.writeValueAsString(stateMap);

            // NodeService를 통해 nodeStateJson 업데이트
            nodeService.updateNodeStateJson(traceId, stateJson);

            log.debug("ToolUse Node state JSON 저장 완료 - traceId: {}", traceId);


        } catch (Exception e) {
            log.error("ToolUse State DB 저장 실패 - traceId: {}", traceId, e);
            // State 저장 실패는 워크플로우를 중단하지 않음
        }
    }
}