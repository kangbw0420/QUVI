package com.daquv.agent.workflow.tooluse.node;

import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.quvi.llmadmin.GenerationService;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.LlmOutputHandler;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import com.daquv.agent.workflow.tooluse.ToolUsePromptBuilder;
import com.daquv.agent.workflow.util.LLMRequest;
import com.daquv.agent.quvi.util.WebSocketUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class FunkNode implements WorkflowNode {

    @Autowired
    private LLMRequest llmService;

    @Autowired
    private ToolUsePromptBuilder promptBuilder;

    @Autowired
    private GenerationService generationService;

    @Autowired
    private WebSocketUtils webSocketUtils;

    @Autowired
    private RequestProfiler requestProfiler;

    @Override
    public String getId() {
        return "funk";
    }

    @Override
    public void execute(WorkflowState state) {
        String userQuestion = state.getUserQuestion();
        String chainId = state.getWorkflowId();

        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("사용자 질문이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다."));
            return;
        }

        log.info("API 함수 선택 처리 중: {}", userQuestion);

        try {
            // WebSocket 메시지 전송
            webSocketUtils.sendNodeStart(state.getWebSocketSession(), "funk");

            // QnA ID 생성
            String qnaId = generationService.createQnaId(state.getNodeId());

            // History 조회
            List<Map<String, Object>> funkHistory = promptBuilder.getFunkHistory(chainId);

            // Funk 프롬프트 생성 (QnA ID 포함)
            PromptBuilder.PromptWithRetrieveTime promptWithTime = promptBuilder.buildFunkPromptWithFewShots(userQuestion, funkHistory, qnaId, chainId);
            PromptTemplate promptTemplate = promptWithTime.getPromptTemplate();
            String prompt = promptTemplate.build();

            // 질문 기록
            log.info("===== funk(Q) =====");

            // LLM 호출하여 API 선택 with 프로파일링
            long startTime = System.currentTimeMillis();
            String llmResponse = llmService.callQwenLlm(prompt, qnaId, chainId);
            long endTime = System.currentTimeMillis();

            // LLM 프로파일링 기록
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordLlmCall(chainId, elapsedTime, "funk");

            String selectedApi = LlmOutputHandler.extractAnswer(llmResponse);

            // "ai:" 접두사 제거
            selectedApi = LlmOutputHandler.handleAiColon(selectedApi);

            if (selectedApi == null || selectedApi.trim().isEmpty()) {
                log.error("API 선택 실패");
                state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("LLM_ERROR", "API 선택에 실패했습니다."));
                return;
            }

            // 답변 기록
            log.info("===== funk(A) =====");
            log.info("선택된 API: {}", selectedApi);
            // 상태 업데이트
            state.setSelectedApi(selectedApi);

            log.info("API 함수 선택 완료: {}", selectedApi);

        } catch (Exception e) {
            log.error("FunkNode 실행 중 예외 발생: {}", e.getMessage(), e);
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("FUNK_ERROR", "API 선택 중 오류가 발생했습니다."));
        }
    }
}