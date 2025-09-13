package com.daquv.agent.integration.context;

import com.daquv.agent.quvi.admin.NodeService;
// import com.daquv.agent.quvi.admin.WorkflowService;
import com.daquv.agent.quvi.util.NodeExecutor;
import com.daquv.agent.quvi.util.WorkflowStateManager;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState;
import com.daquv.agent.workflow.util.SaveStateUtil;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.Map;

@Component
@Slf4j
public class SemanticQueryWorkflowContext {

    @Autowired
    private WorkflowStateManager<SemanticQueryWorkflowState> stateManager;

    @Autowired
    private NodeExecutor nodeExecutor;

    @Autowired
    private NodeService nodeService;

    // @Autowired
    // private WorkflowService workflowService;

    /**
     * SemanticQuery 워크플로우 실행
     * - DSL 경로: extractMetrics -> extractFilter -> manipulation -> dsl2sql
     */
    public void executeSemanticQueryWorkflow(SemanticQueryWorkflowState semanticQueryState) {
        String workflowId = semanticQueryState.getWorkflowId();

        try {
            // executeNode("semanticQueryNextPageNode", semanticQueryState);

            // if ("next_page".equals(semanticQueryState.getSplitedQuestion())) {
            //     log.info("next_page 요청 처리 완료 - workflowId: {}", workflowId);
            //     // finalAnswer는 Supervisor에서 관리하므로 여기서는 워크플로우만 완료
            //     workflowService.completeWorkflow(workflowId, "next_page 처리 완료");
            //     stateManager.updateState(workflowId, semanticQueryState);
            //     return;
            // }

            // 0. DateChecker Node - 날짜 정보 확인 및 HIL 처리
            nodeExecutor.executeNode("dateCheckerNode", semanticQueryState);

            // HIL 상태 체크 - 날짜 명확화가 필요한 경우 워크플로우 중단
            if (semanticQueryState.getDateClarificationNeeded() != null && semanticQueryState.getDateClarificationNeeded()) {
                log.info("SemanticQuery: 날짜 명확화가 필요하여 워크플로우를 대기 상태로 전환합니다.");

                SaveStateUtil.saveSemanticQueryState(nodeService, semanticQueryState.getNodeId(), semanticQueryState);

                log.info("=== SemanticQuery DSL 워크플로우 대기 상태 - workflowId: {} ===", workflowId);
                return; // 워크플로우 중단, 사용자 입력 대기
            }

            // 1. ExtractMetrics Node - 메트릭과 그룹바이 추출
            nodeExecutor.executeNode("extractMetricsNode", semanticQueryState);

            // DSL이 생성되었는지 확인
            if (semanticQueryState.getDsl() == null) {
                log.error("SemanticQuery: ExtractMetrics에서 DSL 추출 실패");
                return;
            }

            // 2. ExtractFilter Node - 필터 추출 및 적용
            nodeExecutor.executeNode("extractFilterNode", semanticQueryState);

            // 3. Manipulation Node - order by/limit 추출 및 커스텀 조작
            nodeExecutor.executeNode("manipulationNode", semanticQueryState);

            // 4. Dsl2Sql Node - DSL을 SQL로 변환
            nodeExecutor.executeNode("dsl2SqlNode", semanticQueryState);

            // 변경된 State 저장
            stateManager.updateState(workflowId, semanticQueryState);

            log.info("=== SemanticQuery DSL 워크플로우 실행 완료 - workflowId: {} ===", workflowId);

        } catch (Exception e) {
            stateManager.updateState(workflowId, semanticQueryState);
            throw e;
        }
    }

    /**
     * HIL 이후 워크플로우 재개 (날짜 정보가 명확해진 후)
     */
    public void resumeSemanticQueryWorkflow(String workflowId, Map<String, Object> userInput) {
        SemanticQueryWorkflowState semanticQueryState = stateManager.getState(workflowId);
        if (semanticQueryState == null) {
            throw new IllegalStateException("Workflow ID에 해당하는 State를 찾을 수 없습니다: " + workflowId);
        }

        log.info("=== SemanticQuery 워크플로우 재개 - 날짜 명확화 후 - workflowId: {} ===", workflowId);

        try {
            // userInput에서 fromDate, toDate 추출해서 state의 startDate, endDate 업데이트
            semanticQueryState.setStartDate((String) userInput.get("fromDate"));
            semanticQueryState.setEndDate((String) userInput.get("toDate"));

            // HIL 상태 초기화
            semanticQueryState.clearHilState();

            nodeExecutor.executeNode("extractMetricsNode", semanticQueryState);
            nodeExecutor.executeNode("extractFilterNode", semanticQueryState);
            nodeExecutor.executeNode("manipulationNode", semanticQueryState);
            nodeExecutor.executeNode("dsl2SqlNode", semanticQueryState);

            stateManager.updateState(workflowId, semanticQueryState);

            log.info("=== SemanticQuery 워크플로우 재개 완료 - workflowId: {} ===", workflowId);

        } catch (Exception e) {
            log.error("SemanticQuery 워크플로우 재개 실패 - workflowId: {}", workflowId, e);
            stateManager.updateState(workflowId, semanticQueryState);
            throw e;
        }
    }
}