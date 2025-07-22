package com.daquv.agent.workflow.node;

import com.daquv.agent.quvi.llmadmin.GenerationService;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.LlmOutputHandler;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.util.WebSocketUtils;
import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import com.daquv.agent.workflow.util.LLMRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.w3c.dom.stylesheets.LinkStyle;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

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

        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("사용자 질문이 없습니다.");
            state.setSqlError("사용자 질문이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다."));
            return;
        }

        try {
            webSocketUtils.sendNodeStart(state.getWebSocketSession(), "supervisor");


            List<Map<String, Object>> supervisorHistory = promptBuilder.getSupervisorHistory(workflowId);

            PromptTemplate promptTemplate = promptBuilder.buildSupervisorPrompt(userQuestion, supervisorHistory);
            String prompt = promptTemplate.build();

            long startTime = System.currentTimeMillis();
            String llmResponse = llmRequest.callQwenLlm(prompt, null, workflowId);
            long endTime = System.currentTimeMillis();

            // LLM 프로파일링 기록
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordLlmCall(workflowId, elapsedTime, "supervisor");

            String selectedWorkflow = LlmOutputHandler.extractAnswer(llmResponse);
            selectedWorkflow = LlmOutputHandler.handleAiColon(selectedWorkflow);

            if (selectedWorkflow == null || selectedWorkflow.trim().isEmpty()) {
                log.error("워크플로우 선택에 실패했습니다.");
                state.setSelectedWorkflow("DEFAULT"); // 기본 워크플로우로 폴백
                state.setFinalAnswer("워크플로우를 선택하지 못했지만 기본 처리를 진행합니다.");
                return;
            }

            // 선택된 워크플로우 정규화 (대소문자 통일)
            selectedWorkflow = selectedWorkflow.toUpperCase().trim();

            log.info("선택된 워크플로우: {}", selectedWorkflow);
            state.setSelectedWorkflow(selectedWorkflow);

            // QnA 답변 기록
//            generationService.recordAnswer(null, selectedWorkflow, null);

            // WebSocket 메시지 전송
            Map<String, Object> data = new HashMap<>();
            data.put("selected_workflow", selectedWorkflow);
            webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "supervisor", data);

            log.info("Supervisor 워크플로우 선택 완료: {}", selectedWorkflow);

        } catch (Exception e) {
            log.error("SupervisorNode 실행 중 예외 발생: {}", e.getMessage(), e);
            state.setSelectedWorkflow("ERROR");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("SUPERVISOR_ERROR", "워크플로우 선택 중 오류가 발생했습니다."));
        }
    }
}
