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

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class NodataNode implements WorkflowNode {

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
        return "nodata";
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

        log.info("데이터 없음 답변 생성 시작: {}", userQuestion);

        // QnA ID 생성
        String qnaId = qnaService.createQnaId(state.getTraceId());
        
        // History 조회
        List<Map<String, Object>> nodataHistory = promptBuilder.getNodataHistory(chainId);
        
        // Nodata 프롬프트 생성 (history 포함)
        PromptTemplate promptTemplate = promptBuilder.buildNodataPromptWithHistory(userQuestion, nodataHistory);
        String prompt = promptTemplate.build();
        
        // LLM 호출하여 데이터 없음 답변 생성
        String llmResponse = llmService.callDevstral(prompt, qnaId);
        String finalAnswer = LlmOutputHandler.extractAnswer(llmResponse);

        if (finalAnswer == null || finalAnswer.trim().isEmpty()) {
            log.error("데이터 없음 답변 생성에 실패했습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("LLM_ERROR", "데이터 없음 답변 생성에 실패했습니다."));
            return;
        }

        // 미래 날짜 관련 처리
        if (state.getFutureDate() != null && state.getFutureDate()) {
            finalAnswer = "요청주신 시점은 제가 조회가 불가능한 시점이기에 오늘 날짜를 기준으로 조회했습니다. " + finalAnswer;
        }

        log.info("데이터 없음 답변 생성 완료: {}", finalAnswer);
        state.setFinalAnswer(finalAnswer);
        
        // WebSocket 메시지 전송 (node.py의 nodata 참고)
        webSocketUtils.sendNodeStart(state.getWebSocketSession(), "nodata");
    }
}