package com.daquv.agent.workflow.killjoy;

import com.daquv.agent.quvi.llmadmin.NodeService;
import com.daquv.agent.workflow.killjoy.node.KilljoyNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

@Component
@Slf4j
public class KilljoyWorkflowExecutionContext {

    @Autowired
    private ApplicationContext applicationContext;

    @Autowired
    private NodeService nodeService;

    /**
     * Killjoy 워크플로우 실행
     * @param workflowId 워크플로우 ID
     * @param userQuestion 사용자 질문
     * @return 최종 답변
     */
    public String executeKilljoyWorkflow(String workflowId, String userQuestion) {
        log.info("=== Killjoy 워크플로우 실행 시작 - workflowId: {} ===", workflowId);

        String nodeId = null;
        String finalAnswer = null;

        try {
            // KilljoyNode 실행
            KilljoyNode killjoyNode = applicationContext.getBean(KilljoyNode.class);

            // 1. Node 생성
            nodeId = nodeService.createNode(workflowId, killjoyNode.getId());

            // 2. 노드 실행
            finalAnswer = killjoyNode.execute(userQuestion, workflowId, nodeId);

            // 3. Trace 완료
            nodeService.completeNode(nodeId);

            log.info("=== Killjoy 워크플로우 실행 완료 - workflowId: {} ===", workflowId);
            return finalAnswer;

        } catch (Exception e) {
            log.error("Killjoy 워크플로우 실행 실패 - workflowId: {}", workflowId, e);

            // Trace 오류 상태로 변경
            if (nodeId != null) {
                try {
                    nodeService.markTraceError(nodeId);
                } catch (Exception traceError) {
                    log.error("Killjoy Trace 오류 기록 실패: {}", traceError.getMessage());
                }
            }

            return "일상 대화 처리 중 오류가 발생했습니다.";
        }
    }
}