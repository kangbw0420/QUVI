package com.daquv.agent.workflow.node;

import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.quvi.llmadmin.QnaService;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.LlmOutputHandler;
import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import com.daquv.agent.quvi.requests.FstringRequest;
import com.daquv.agent.workflow.util.LLMRequest;
import com.daquv.agent.workflow.util.PipeTable;
import com.daquv.agent.quvi.util.WebSocketUtils;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class RespondentNode implements WorkflowNode {

    @Autowired
    private LLMRequest llmService;

    @Autowired
    private PromptBuilder promptBuilder;
    
    @Autowired
    private QnaService qnaService;

    @Autowired
    private PipeTable pipeTable;

    private final FstringRequest fstringRequest;
    
    @Autowired
    private WebSocketUtils webSocketUtils;

    public RespondentNode(FstringRequest fstringRequest) {
        this.fstringRequest = fstringRequest;
    }

    @Override
    public String getId() {
        return "respondent";
    }

    @Override
    public void execute(WorkflowState state) {
        String userQuestion = state.getUserQuestion();
        List<Map<String, Object>> queryResult = state.getQueryResult();
        String chainId = state.getChainId();

        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("사용자 질문이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다."));
            return;
        }

        if (queryResult == null || queryResult.isEmpty()) {
            log.error("쿼리 결과가 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("NO_DATA", "쿼리 결과가 없습니다."));
            return;
        }

        log.info("=== RespondentNode 실행 시작 ===");
        log.info("사용자 질문: {}", userQuestion);
        log.info("쿼리 결과 행 수: {}", queryResult.size());
        log.info("체인 ID: {}", chainId);
        log.info("hasNext 상태: {}", state.getHasNext());
        log.info("totalRows: {}", state.getTotalRows());

        // 테이블 파이프 생성
        log.info("1단계: 테이블 파이프 생성 시작");
        String tablePipe = pipeTable.pipeTable(queryResult);
        state.setTablePipe(tablePipe);
        log.info("테이블 파이프 생성 완료");

        // QnA ID 생성
        log.info("2단계: QnA ID 생성");
        String qnaId = qnaService.createQnaId(state.getTraceId());
        log.info("생성된 QnA ID: {}", qnaId);
        
        // History 조회
        log.info("3단계: 응답 히스토리 조회");
        List<Map<String, Object>> respondentHistory = promptBuilder.getRespondentHistory(chainId);
        log.info("조회된 히스토리 개수: {}", respondentHistory != null ? respondentHistory.size() : 0);
        
        // hasNext에 따른 프롬프트 분기
        log.info("4단계: hasNext 상태에 따른 프롬프트 분기");
        PromptTemplate promptTemplate;
        if (state.getHasNext() != null && state.getHasNext()) {
            // 페이지네이션 응답 생성
            log.info("✅ 페이지네이션 응답 생성 시작");
            Integer totalRows = state.getTotalRows();
            if (totalRows == null) totalRows = 0;
            
            log.info("페이지네이션용 프롬프트 생성 - 총 행 수: {}", totalRows);
            promptTemplate = promptBuilder.buildPageRespondentPrompt(userQuestion, totalRows, respondentHistory, qnaId);
        } else {
            // 일반 응답 생성
            log.info("❌ 일반 응답 생성 시작 (hasNext: false)");
            promptTemplate = promptBuilder.buildRespondentPromptWithFewShotsAndHistory(
                userQuestion, tablePipe, respondentHistory, qnaId);
        }
        
        log.info("5단계: 프롬프트 생성 및 LLM 호출");
        String prompt = promptTemplate.build();
        log.info("생성된 프롬프트 길이: {} 문자", prompt.length());
        
        // LLM 호출하여 응답 생성
        String llmResponse = llmService.callDevstral(prompt, qnaId);
        log.info("LLM 응답 길이: {} 문자", llmResponse != null ? llmResponse.length() : 0);
        
        String fstringAnswer = LlmOutputHandler.extractFStringAnswer(llmResponse);

        if (fstringAnswer == null || fstringAnswer.trim().isEmpty()) {
            log.error("fstring 응답 생성에 실패했습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("LLM_ERROR", "fstring 응답 생성에 실패했습니다."));
            return;
        }

        log.info("6단계: fstring 응답 처리");
        log.info("추출된 fstring 응답: {}", fstringAnswer);
        state.setFString(fstringAnswer);
        
        String finalAnswer = fstringRequest.computeFString(fstringAnswer, queryResult);
        state.setFinalAnswer(finalAnswer);
        
        log.info("=== RespondentNode 실행 완료 ===");
        log.info("최종 응답 길이: {} 문자", finalAnswer != null ? finalAnswer.length() : 0);
        log.info("최종 상태 - hasNext: {}, totalRows: {}, finalAnswer: {}", 
                state.getHasNext(), state.getTotalRows(), 
                finalAnswer != null ? finalAnswer.substring(0, Math.min(100, finalAnswer.length())) + "..." : "null");
        
        // WebSocket 메시지 전송 (node.py의 respondent 참고)
        Map<String, Object> data = new HashMap<>();
        data.put("result_row", queryResult.size());
        data.put("result_column", queryResult.isEmpty() ? 0 : queryResult.get(0).size());
        webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "respondent", data);
    }
}