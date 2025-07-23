package com.daquv.agent.workflow;

import com.daquv.agent.quvi.llmadmin.GenerationService;
import com.daquv.agent.quvi.util.LlmOutputHandler;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.util.WebSocketUtils;
import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import com.daquv.agent.workflow.util.LLMRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.*;

@Slf4j
@Component
public class SupervisorNode implements WorkflowNode {
    // input - user_question -> output : 어디로 가야하는지 node

    @Autowired
    private LLMRequest llmRequest;

    @Autowired
    private PromptBuilder promptBuilder;

    @Autowired
    private GenerationService generationService;

    @Autowired
    private WebSocketUtils webSocketUtils;

    @Autowired
    private RequestProfiler requestProfiler;


    @Override
    public String getId() {
        return "supervisor";
    }

    @Override
    public void execute(WorkflowState state) {
        String userQuestion = state.getUserQuestion();
        String workflowId = state.getWorkflowId();

        String selectedWorkflow = selectWorkflow(userQuestion, workflowId);
        state.setSelectedWorkflow(selectedWorkflow);

        // WebSocket 메시지 전송 (WebSocket 세션이 있는 경우만)
        if (state.getWebSocketSession() != null) {
            try {
                Map<String, Object> data = new HashMap<>();
                data.put("selected_workflow", selectedWorkflow);
                webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "supervisor", data);
            } catch (Exception e) {
                log.warn("WebSocket 메시지 전송 실패: {}", e.getMessage());
            }
        }
    }

    public String selectWorkflow(String userQuestion, String workflowId) {
        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("사용자 질문이 없습니다.");
            return "DEFAULT";
        }

        try {
            PromptTemplate promptTemplate = promptBuilder.buildSupervisorPrompt(userQuestion, new ArrayList<>());
            String prompt = promptTemplate.build();

            if (prompt == null || prompt.trim().isEmpty()) {
                log.error("생성된 프롬프트가 비어있습니다. 기본 워크플로우로 진행합니다.");
                return "DEFAULT";
            }

            log.info("생성된 Supervisor 프롬프트 길이: {}", prompt.length());
            log.debug("Supervisor 프롬프트 내용: {}", prompt);

            long startTime = System.currentTimeMillis();
            String llmResponse = llmRequest.callQwenLlm(prompt, null, workflowId);
            long endTime = System.currentTimeMillis();

            // LLM 프로파일링 기록
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordLlmCall(workflowId, elapsedTime, "supervisor");

            String selectedWorkflow = LlmOutputHandler.extractWorkflowSelection(llmResponse);
            selectedWorkflow = LlmOutputHandler.handleAiColon(selectedWorkflow);

            if (selectedWorkflow == null || selectedWorkflow.trim().isEmpty()) {
                log.error("워크플로우 선택에 실패했습니다.");
                return "DEFAULT";
            }

            // 선택된 워크플로우 정규화
            selectedWorkflow = selectedWorkflow.toUpperCase().trim();

            // 유효한 워크플로우인지 검증
            if (!isValidWorkflow(selectedWorkflow)) {
                log.warn("유효하지 않은 워크플로우 선택됨: '{}'. DEFAULT로 변경합니다.", selectedWorkflow);
                selectedWorkflow = "DEFAULT";
            }

            log.info("최종 선택된 워크플로우: {}", selectedWorkflow);
            return selectedWorkflow;

        } catch (Exception e) {
            log.error("SupervisorNode 워크플로우 선택 중 예외 발생: {}", e.getMessage(), e);
            return "DEFAULT";
        }
    }

    /**
     * 유효한 워크플로우인지 검증
     */
    private boolean isValidWorkflow(String workflow) {
        return Arrays.asList("JOY", "TOOLUSE", "SEMANTICQUERY").contains(workflow);
    }
}
