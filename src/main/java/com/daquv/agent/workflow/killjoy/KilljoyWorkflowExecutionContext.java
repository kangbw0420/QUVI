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

            // 4. State DB 저장 (최소한의 정보만)
            saveStateToDatabase(nodeId, userQuestion, finalAnswer);

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

    /**
     * 최소한의 State를 DB에 저장
     */
    private void saveStateToDatabase(String traceId, String userQuestion, String finalAnswer) {
        try {
            Map<String, Object> stateMap = new HashMap<>();

            // 히스토리 조회에 필요한 최소한의 필드들만 저장
            if (userQuestion != null) {
                stateMap.put("userQuestion", userQuestion);
            }
            if (finalAnswer != null) {
                stateMap.put("finalAnswer", finalAnswer);
            }

            ObjectMapper objectMapper = new ObjectMapper();
            String stateJson = objectMapper.writeValueAsString(stateMap);
            nodeService.updateNodeStateJson(traceId, stateJson);

        } catch (Exception e) {
            log.error("Killjoy State DB 저장 실패 - traceId: {}", traceId, e);
            // State 저장 실패는 워크플로우를 중단하지 않음
        }
    }
}