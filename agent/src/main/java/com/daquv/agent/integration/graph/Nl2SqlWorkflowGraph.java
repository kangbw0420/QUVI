package com.daquv.agent.integration.graph;

import com.daquv.agent.quvi.util.NodeExecutor;
import com.daquv.agent.quvi.util.WorkflowStateManager;
import com.daquv.agent.workflow.nl2sql.Nl2SqlWorkflowState;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;


@Component
@Slf4j
public class Nl2SqlWorkflowGraph {

    @Autowired
    private WorkflowStateManager<Nl2SqlWorkflowState> stateManager;

    @Autowired
    private NodeExecutor nodeExecutor;

    /**
     * NL2SQL 워크플로우 실행2
     * - 일반 요청: Dater -> Nl2sql
     * - next_page 요청: NextPage
     */
    public void executeNl2SqlWorkflow(Nl2SqlWorkflowState nl2SqlState) {
        if (nl2SqlState == null) {
            throw new IllegalStateException("State가 null입니다.");
        }
        
        String workflowId = nl2SqlState.getWorkflowId();
        log.info("=== NL2SQL 워크플로우 시작 - workflowId: {} ===", workflowId);

        try {

            // next_page 요청인 경우: 기존 SQL 재사용하여 페이지네이션만 처리
            // if ("next_page".equals(state.getUserQuestion())) {
            //     log.info("next_page 요청 감지 - 페이지네이션 처리");
            //     executeNode(nextPageNode, state, "NextPage");
            //     executeFinalResponse(state);
            //     return;
            // }

            // 0. Commander 실행 (테이블 선택)
            nodeExecutor.executeNode("commanderNode", nl2SqlState);

            // 일반 워크플로우 실행
            // 1. Dater 실행 (HIL 없는 버전)
            nodeExecutor.executeNode("daterNode", nl2SqlState);

            // 날짜 정보가 없는 경우 워크플로우 종료
            if (!nl2SqlState.hasDateInfo()) {
                log.warn("날짜 정보가 설정되지 않아 워크플로우를 종료합니다.");
                stateManager.updateState(nl2SqlState.getWorkflowId(), nl2SqlState);
                return;
            }

            // 2. Nl2sql 실행 (SQL 생성)
            nodeExecutor.executeNode("nl2sqlNode", nl2SqlState);

            log.info("=== NL2SQL 워크플로우 완료 - workflowId: {} ===", workflowId);

        } catch (Exception e) {
            stateManager.updateState(workflowId, nl2SqlState);
            throw e;
        }
    }
}