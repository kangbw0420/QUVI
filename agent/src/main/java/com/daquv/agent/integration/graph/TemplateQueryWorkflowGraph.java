package com.daquv.agent.integration.graph;

import com.daquv.agent.quvi.util.NodeExecutor;
import com.daquv.agent.quvi.util.WorkflowStateManager;
import com.daquv.agent.workflow.templatequery.TemplateQueryWorkflowState;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import lombok.extern.slf4j.Slf4j;

@Component
@Slf4j
public class TemplateQueryWorkflowGraph {

    @Autowired
    private WorkflowStateManager<TemplateQueryWorkflowState> stateManager;

    @Autowired
    private NodeExecutor nodeExecutor;

    /**
     * TemplateQuery 워크플로우 실행
     * - NextPage 처리
     * - API 경로: funk -> params -> (yqmd or executor) -> respondent
     */
    public void executeTemplateQueryWorkflow(TemplateQueryWorkflowState templateQueryState) {
        if (templateQueryState == null) {
            throw new IllegalStateException("State가 null입니다.");
        }
        
        String workflowId = templateQueryState.getWorkflowId();

        log.info("=== TemplateQuery 워크플로우 실행 시작 - workflowId: {} ===", workflowId);

        try {
            // 1. Funk Node - API 함수 선택
            nodeExecutor.executeNode("funkNode", templateQueryState);
            
            // 2. Params Node - API 파라미터 추출
            nodeExecutor.executeNode("paramsNode", templateQueryState);

            // params 조건부 엣지 - 잘못된 날짜인 경우 종료
            if (templateQueryState.getInvalidDate() != null && templateQueryState.getInvalidDate()) {
                log.info("invalid_date 감지 - TemplateQuery 워크플로우 종료");
                return;
            }

            // 3. YQMD Node (aicfo_get_financial_flow API인 경우에만)
            if ("aicfo_get_financial_flow".equals(templateQueryState.getSelectedApi())) {
                nodeExecutor.executeNode("yqmdNode", templateQueryState);
            }

            // 변경된 State 저장
            stateManager.updateState(workflowId, templateQueryState);

            log.info("=== TemplateQuery 워크플로우 실행 완료 - workflowId: {} ===", workflowId);

        } catch (Exception e) {
            stateManager.updateState(workflowId, templateQueryState);
            throw e;
        }
    }
}