package com.daquv.agent.workflow.semanticquery.node;

import com.daquv.agent.quvi.llmadmin.GenerationService;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.LlmOutputHandler;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.util.WebSocketUtils;
import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptBuilder.PromptWithRetrieveTime;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import com.daquv.agent.workflow.util.DateUtils;
import com.daquv.agent.workflow.util.LLMRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Component
@Slf4j
public class DaterNode implements WorkflowNode {

    @Autowired
    private PromptBuilder promptBuilder;

    @Autowired
    private GenerationService generationService;

    @Autowired
    private LLMRequest llmService;

    @Autowired
    private WebSocketUtils webSocketUtils;

    @Autowired
    private RequestProfiler requestProfiler;

    @Override
    public String getId() {
        return "dater";
    }

    @Override
    public void execute(WorkflowState state) {
        String userQuestion = state.getUserQuestion();
        String selectedTable = state.getSelectedTable();
        String chainId = state.getWorkflowId();

        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("사용자 질문이 없습니다.");
            state.setSqlError("사용자 질문이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다."));
            return;
        }

        if (selectedTable == null || selectedTable.trim().isEmpty()) {
            log.error("선택된 테이블이 없습니다.");
            state.setSqlError("선택된 테이블이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("TABLE_SELECTION_ERROR", "선택된 테이블이 없습니다."));
            return;
        }

        // QnA ID 생성
        String qnaId = generationService.createQnaId(state.getNodeId());

        // History 조회
        List<Map<String, Object>> daterHistory = promptBuilder.getDaterHistory(chainId);

        // Dater 프롬프트 생성 (few-shot + history 포함 + QnA 저장)
        PromptWithRetrieveTime promptResult = promptBuilder.buildDaterPromptWithFewShots(
                selectedTable, userQuestion, daterHistory, qnaId, chainId);
        PromptTemplate promptTemplate = promptResult.getPromptTemplate();
        BigDecimal retrieveTime = promptResult.getRetrieveTime();

        String prompt = promptTemplate.build();
        long startTime = System.currentTimeMillis();
        String llmResponse = llmService.callQwenLlm(prompt, qnaId, chainId);
        long endTime = System.currentTimeMillis();

        // LLM 프로파일링 기록
        double elapsedTime = (endTime - startTime) / 1000.0;
        requestProfiler.recordLlmCall(chainId, elapsedTime, "dater");

        // JSON 응답에서 날짜 정보 추출
        Map<String, String> dateInfo = LlmOutputHandler.extractDateInfo(llmResponse);

        if (dateInfo == null || !dateInfo.containsKey("from_date") || !dateInfo.containsKey("to_date")) {
            log.error("날짜 정보 추출에 실패했습니다.");
            state.setSqlError("날짜 정보 추출에 실패했습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("DATE_EXTRACTION_ERROR", "날짜 정보 추출에 실패했습니다."));
            return;
        }

        String fromDate = dateInfo.get("from_date");
        String toDate = dateInfo.get("to_date");

        // 미래 날짜 교정 (Python과 동일한 로직)
        String today = DateUtils.getTodayStr();
        if (DateUtils.isFutureDate(fromDate)) {
            log.warn("Future from_date: {}, correcting to today: {}", fromDate, today);
            fromDate = today;
             state.setFutureDate(true);
        }

        if (DateUtils.isFutureDate(toDate)) {
            log.warn("Future to_date: {}, correcting to today: {}", toDate, today);
            toDate = today;
            state.setFutureDate(false);
        }

        log.info("Final parameters: from_date={}, to_date={}", fromDate, toDate);

        // Python과 동일하게 QnA 응답 기록
        String outputStr = String.format("{\"from_date\": \"%s\", \"to_date\": \"%s\"}", fromDate, toDate);
        generationService.recordAnswer(qnaId, outputStr, retrieveTime);

        // 상태에 날짜 정보 저장
        state.setStartDate(fromDate);
        state.setEndDate(toDate);

        // WebSocket 메시지 전송 (기존 websocket 은 executor, nl2sql, safeguard, nodata, killjoy 에만... 끝난 WebSocket 로직 있어서 추가)
        Map<String, Object> data = new HashMap<>();
        data.put("from_date", fromDate);
        data.put("to_date", toDate);
        webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "dater", data);

        log.info("날짜 정보 추출 완료: from_date={}, to_date={}", fromDate, toDate);
    }
}
