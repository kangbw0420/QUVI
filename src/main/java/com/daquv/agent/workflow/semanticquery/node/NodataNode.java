package com.daquv.agent.workflow.semanticquery.node;

import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.quvi.llmadmin.GenerationService;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.LlmOutputHandler;
import com.daquv.agent.workflow.dto.VectorNotes;
import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowNode;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState;
import com.daquv.agent.workflow.util.LLMRequest;
import com.daquv.agent.quvi.util.WebSocketUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class NodataNode implements SemanticQueryWorkflowNode {

    @Autowired
    private LLMRequest llmService;

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
        return "nodata";
    }

    @Override
    public void execute(SemanticQueryWorkflowState state) {
        String userQuestion = state.getUserQuestion();
        String chainId = state.getWorkflowId();
        Boolean noteChanged = state.getNoteChanged();
        // WebSocket 메시지 전송 (node.py의 nodata 참고)
        webSocketUtils.sendNodeStart(state.getWebSocketSession(), "nodata");

        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("사용자 질문이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다."));
            return;
        }

        if (noteChanged) {
            log.info("노트 변화 감지");
            VectorNotes vectorNotes = state.getVectorNotes();
            String vectorNotesStr = String.join(", ", vectorNotes.getVectorNotes());
            userQuestion += String.format(" 유사한 노트 ('%s')를 활용해서도 검색해줘", vectorNotesStr);
        }

        log.info("데이터 없음 답변 생성 시작: {}", userQuestion);

        // QnA ID 생성
        String qnaId = generationService.createQnaId(state.getNodeId());
        
        // History 조회
        List<Map<String, Object>> nodataHistory = promptBuilder.getNodataHistory(chainId);
        
        // Nodata 프롬프트 생성 (history 포함)
        PromptTemplate promptTemplate = promptBuilder.buildNodataPromptWithHistory(userQuestion, nodataHistory);
        String prompt = promptTemplate.build();
        
        // LLM 호출하여 데이터 없음 답변 생성
        long startTime = System.currentTimeMillis();
        String llmResponse = llmService.callQwenLlm(prompt, qnaId);
        long endTime = System.currentTimeMillis();

        // LLM 프로파일링 기록
        double elapsedTime = (endTime - startTime) / 1000.0;
        requestProfiler.recordLlmCall(chainId, elapsedTime, "nodata");
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
    }
}