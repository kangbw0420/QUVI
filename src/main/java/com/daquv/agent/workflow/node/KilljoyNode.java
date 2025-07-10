package com.daquv.agent.workflow.node;

import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.quvi.llmadmin.QnaService;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.LlmOutputHandler;
import com.daquv.agent.workflow.prompt.PromptBuilder;
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
public class KilljoyNode implements WorkflowNode {

    @Autowired
    private LLMRequest llmService;

    @Autowired
    private PromptBuilder promptBuilder;
    
    @Autowired
    private QnaService qnaService;
    
    @Autowired
    private WebSocketUtils webSocketUtils;

    @Override
    public String getId() {
        return "killjoy";
    }

    @Override
    public void execute(WorkflowState state) {
        String userQuestion = state.getUserQuestion();
        String chainId = state.getChainId();

        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("사용자 질문이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다."));
            return;
        }

        log.info("비재무 질문 처리 중: {}", userQuestion);

        try {
            // WebSocket 메시지 전송
            webSocketUtils.sendNodeStart(state.getWebSocketSession(), "killjoy");

            // QnA ID 생성
            String qnaId = qnaService.createQnaId(state.getTraceId());
            
            // History 조회
            List<Map<String, Object>> killjoyHistory = promptBuilder.getKilljoyHistory(chainId);
            
            // Killjoy 프롬프트 생성
            PromptTemplate promptTemplate = promptBuilder.buildKilljoyPromptWithHistory(userQuestion, killjoyHistory);
            String prompt = promptTemplate.build();
            
            // 질문 기록
            log.info("===== killjoy(Q) ====");
            // LLM 호출하여 역할 안내 답변 생성
            String llmResponse = llmService.callQwenHigh(prompt, qnaId, chainId);
            String finalAnswer = LlmOutputHandler.extractAnswer(llmResponse);

            if (finalAnswer == null || finalAnswer.trim().isEmpty()) {
                log.error("역할 안내 답변 생성에 실패했습니다.");
                state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("LLM_ERROR", "역할 안내 답변 생성에 실패했습니다."));
                return;
            }

            // 답변 기록
            log.info("===== killjoy(A) ====");
            log.info("생성된 응답: {}...", finalAnswer.length() > 100 ? finalAnswer.substring(0, 100) : finalAnswer);
            // 상태 업데이트
            state.setFinalAnswer(finalAnswer);
            state.setQueryResult(null);
            state.setSqlQuery("");
            state.setSelectedTable("");
            
            log.info("비재무 질문 처리 완료: {}", finalAnswer);
            
        } catch (Exception e) {
            log.error("KilljoyNode 실행 중 예외 발생: {}", e.getMessage(), e);
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("KILLJOY_ERROR", "비재무 질문 처리 중 오류가 발생했습니다."));
        }
    }
} 