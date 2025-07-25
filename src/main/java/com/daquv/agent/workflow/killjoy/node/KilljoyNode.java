package com.daquv.agent.workflow.killjoy.node;

import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.llmadmin.GenerationService;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.LlmOutputHandler;
import com.daquv.agent.workflow.killjoy.KillJoyPromptBuilder;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import com.daquv.agent.workflow.util.LLMRequest;
import com.daquv.agent.quvi.util.WebSocketUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class KilljoyNode{

    @Autowired
    private LLMRequest llmService;

    @Autowired
    private KillJoyPromptBuilder promptBuilder;
    
    @Autowired
    private GenerationService generationService;
    
    @Autowired
    private WebSocketUtils webSocketUtils;

    @Autowired
    private RequestProfiler requestProfiler;

    public String getId() {
        return "killjoy";
    }

    public String execute(String userQuestion, String workflowId, String nodeId) {
        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("사용자 질문이 없습니다.");
            return ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다.");
        }

        log.info("비재무 질문 처리 중: {}", userQuestion);

        try {
            // QnA ID 생성
            String qnaId = generationService.createQnaId(nodeId);

            // History 조회
            List<Map<String, Object>> killjoyHistory = promptBuilder.getKilljoyHistory(workflowId);

            // Killjoy 프롬프트 생성
            PromptTemplate promptTemplate = promptBuilder.buildKilljoyPromptWithHistory(userQuestion, killjoyHistory);
            String prompt = promptTemplate.build();

            // 질문 기록
            log.info("===== killjoy(Q) ====");

            // LLM 호출하여 역할 안내 답변 생성
            long startTime = System.currentTimeMillis();
            String llmResponse = llmService.callQwenHigh(prompt, qnaId, workflowId);
            long endTime = System.currentTimeMillis();
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordLlmCall(workflowId, elapsedTime, "killjoy");

            String finalAnswer = LlmOutputHandler.extractAnswer(llmResponse);

            if (finalAnswer == null || finalAnswer.trim().isEmpty()) {
                log.error("역할 안내 답변 생성에 실패했습니다.");
                return ErrorHandler.getWorkflowErrorMessage("LLM_ERROR", "역할 안내 답변 생성에 실패했습니다.");
            }

            // 답변 기록
            log.info("===== killjoy(A) ====");
            log.info("생성된 응답: {}...", finalAnswer.length() > 100 ? finalAnswer.substring(0, 100) : finalAnswer);

            log.info("비재무 질문 처리 완료: {}", finalAnswer);
            return finalAnswer;

        } catch (Exception e) {
            log.error("KilljoyNode 실행 중 예외 발생: {}", e.getMessage(), e);
            return ErrorHandler.getWorkflowErrorMessage("KILLJOY_ERROR", "비재무 질문 처리 중 오류가 발생했습니다.");
        }
    }
}
