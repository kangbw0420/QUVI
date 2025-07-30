package com.daquv.agent.workflow.semanticquery.node;

import com.daquv.agent.quvi.util.RequestProfiler;
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
        // WebSocket 메시지 전송 (node.py의 nodata 참고)
        webSocketUtils.sendNodeStart(state.getWebSocketSession(), "nodata");

        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("사용자 질문이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다."));
            return;
        }

        Map<String, SemanticQueryWorkflowState.SemanticQueryExecution> executionMap =
                state.getSemanticQueryExecutionMap();

        boolean allNoData = true;
        boolean hasNoteChanged = false;
        VectorNotes combinedVectorNotes = null;

        for (Map.Entry<String, SemanticQueryWorkflowState.SemanticQueryExecution> entry : executionMap.entrySet()) {
            String entity = entry.getKey();
            SemanticQueryWorkflowState.SemanticQueryExecution execution = entry.getValue();

            log.debug("Checking noData status for entity '{}': noData={}", entity, execution.getNoData());

            if (execution.getNoData() == null || !execution.getNoData()) {
                allNoData = false;
                log.debug("Entity '{}' has data, skipping nodata processing", entity);
            }

            // noteChanged 확인
            if (execution.getNoteChanged() != null && execution.getNoteChanged()) {
                hasNoteChanged = true;
                if (execution.getVectorNotes() != null) {
                    combinedVectorNotes = execution.getVectorNotes();
                    log.info("Entity '{}' has note changes with vector notes", entity);
                }
            }
        }

        if (!allNoData) {
            log.info("일부 execution에 데이터가 있으므로 nodata 처리를 건너뜁니다.");
            return;
        }
        log.info("✅ 모든 execution이 noData 상태입니다. nodata 응답을 생성합니다.");

        // noteChanged가 있는 경우 사용자 질문 보강
        String enhancedUserQuestion = userQuestion;
        if (hasNoteChanged && combinedVectorNotes != null) {
            log.info("노트 변화 감지");
            String vectorNotesStr = String.join(", ", combinedVectorNotes.getVectorNotes());
            enhancedUserQuestion += String.format(" 유사한 노트 ('%s')를 활용해서도 검색해줘", vectorNotesStr);
            log.info("보강된 사용자 질문: {}", enhancedUserQuestion);
        }

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

        log.info("데이터 없음 답변 생성 완료: {}", finalAnswer);
        state.setFinalAnswer(finalAnswer);
    }
}