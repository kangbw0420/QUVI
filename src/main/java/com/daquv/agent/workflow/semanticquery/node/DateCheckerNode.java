package com.daquv.agent.workflow.semanticquery.node;

import com.daquv.agent.quvi.llmadmin.GenerationService;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.LlmOutputHandler;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.util.WebSocketUtils;
import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptBuilder.PromptWithRetrieveTime;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowNode;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState;
import com.daquv.agent.workflow.util.LLMRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Component
@Slf4j
public class DateCheckerNode implements SemanticQueryWorkflowNode {

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
        return "date_checker";
    }

    @Override
    public void execute(SemanticQueryWorkflowState state) {
        String userQuestion = state.getUserQuestion();
        String selectedTable = state.getSelectedTable();
        String chainId = state.getWorkflowId();

        log.info("DateCheckerNode 실행 시작 - userQuestion: {}, selectedTable: {}, chainId: {}",
                userQuestion, selectedTable, chainId);

        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("사용자 질문이 없습니다.");
            setErrorInExecution(state, selectedTable, "사용자 질문이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다."));
            return;
        }
        String tableForPrompt = selectedTable != null ? selectedTable : "AMT";
        log.info("프롬프트용 테이블명: {} (원본: {})", tableForPrompt, selectedTable);
//        if (selectedTable == null || selectedTable.trim().isEmpty()) {
//            log.error("선택된 테이블이 없습니다.");
//            setErrorInExecution(state, selectedTable, "선택된 테이블이 없습니다.");
//            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("TABLE_SELECTION_ERROR", "선택된 테이블이 없습니다."));
//            return;
//        }

        try {
            // QnA ID 생성
            String generationId = generationService.createQnaId(state.getNodeId());

            // History 조회
            List<Map<String, Object>> daterHistory = null;
            try {
                daterHistory = promptBuilder.getDaterHistory(chainId);
                log.info("Dater history 조회 완료: {} 개", daterHistory != null ? daterHistory.size() : 0);
            } catch (Exception e) {
                log.warn("Dater history 조회 실패, 빈 리스트로 진행: {}", e.getMessage());
                daterHistory = new ArrayList<>();
            }

            // Dater 프롬프트 생성 (few-shot + history 포함 + QnA 저장)
            PromptWithRetrieveTime promptResult = promptBuilder.buildDaterPromptWithFewShots(
                    tableForPrompt, userQuestion, daterHistory, generationId, chainId);
            PromptTemplate promptTemplate = promptResult.getPromptTemplate();
            BigDecimal retrieveTime = promptResult.getRetrieveTime();

            String prompt = promptTemplate.build();
            long startTime = System.currentTimeMillis();
            String llmResponse = llmService.callQwenLlm(prompt, generationId, chainId);
            long endTime = System.currentTimeMillis();

            // LLM 프로파일링 기록
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordLlmCall(chainId, elapsedTime, "dater");

            // JSON 응답에서 날짜 정보 추출
            Map<String, String> dateInfo = LlmOutputHandler.extractDateInfo(llmResponse);

            // 날짜 정보가 명확하지 않은 경우 HIL 활성화
            if (dateInfo == null || !dateInfo.containsKey("from_date") || !dateInfo.containsKey("to_date")
                    || isDateUnclear(dateInfo)) {

                log.warn("날짜 정보가 명확하지 않아 사용자 입력이 필요합니다.");

                // HIL 상태 설정
                state.setDateClarificationNeeded(true);
                state.setCurrentNode("date_checker"); // 현재 노드를 기록하여 재개 지점 설정

                // 사용자에게 날짜 명확화 요청 메시지 설정
                String clarificationMessage = generateDateClarificationMessage(userQuestion, dateInfo);
                state.setFinalAnswer(clarificationMessage);

                // WebSocket으로 날짜 입력 요청 전송
                Map<String, Object> hilData = new HashMap<>();
                hilData.put("type", "date_clarification");
                hilData.put("message", clarificationMessage);
                hilData.put("current_question", userQuestion);
                hilData.put("suggested_dates", dateInfo); // 추출된 불명확한 날짜 정보도 함께 전송

                webSocketUtils.sendHilRequest(state.getWebSocketSession(), "date_checker", hilData);

                // QnA 응답 기록 (HIL 요청)
                String outputStr = String.format("{\"hil_required\": true, \"message\": \"%s\"}", clarificationMessage);
                generationService.recordAnswer(generationId, outputStr, retrieveTime);

                log.info("날짜 명확화를 위한 HIL 요청 완료");
                return;
            }

            // 날짜 정보가 명확한 경우 기존 로직 실행
            String fromDate = dateInfo.get("from_date");
            String toDate = dateInfo.get("to_date");

            log.info("Final parameters: from_date={}, to_date={}", fromDate, toDate);

            // Python과 동일하게 QnA 응답 기록
            String outputStr = String.format("{\"from_date\": \"%s\", \"to_date\": \"%s\"}", fromDate, toDate);
            generationService.recordAnswer(generationId, outputStr, retrieveTime);

            // 상태에 날짜 정보 저장
            state.setStartDate(fromDate);
            state.setEndDate(toDate);
            state.setDateClarificationNeeded(false);

            if (state.hasDateInfo()) {
                log.info("날짜 정보 설정 완료 확인: from_date={}, to_date={}", fromDate, toDate);
            } else {
                log.warn("날짜 정보 설정이 완전하지 않습니다.");
            }

            // WebSocket 메시지 전송
            Map<String, Object> data = new HashMap<>();
            data.put("from_date", fromDate);
            data.put("to_date", toDate);
            webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "dater", data);

            log.info("날짜 정보 추출 완료: from_date={}, to_date={}", fromDate, toDate);
        } catch (Exception e) {
            log.error("DateCheckerNode 실행 중 오류 발생", e);
            setErrorInExecution(state, selectedTable, "날짜 확인 중 오류가 발생했습니다: " + e.getMessage());
            state.setFinalAnswer("죄송합니다. 날짜 정보를 확인하는 중 오류가 발생했습니다.");
        }
    }


    /**
     * SemanticQueryExecution에 에러 설정
     */
    private void setErrorInExecution(SemanticQueryWorkflowState state, String tableName, String errorMessage) {
        if (state.getSemanticQueryExecutionMap() == null) {
            state.setSemanticQueryExecutionMap(new HashMap<>());
        }

        String key = tableName != null ? tableName : "default";
        SemanticQueryWorkflowState.SemanticQueryExecution execution =
                state.getSemanticQueryExecutionMap().computeIfAbsent(key,
                        k -> SemanticQueryWorkflowState.SemanticQueryExecution.builder().build());

        execution.setSqlError(errorMessage);
    }

    /**
     * 날짜 정보가 불명확한지 확인
     */
    private boolean isDateUnclear(Map<String, String> dateInfo) {
        String fromDate = dateInfo.get("from_date");
        String toDate = dateInfo.get("to_date");

        // null이거나 빈 문자열인 경우
        if (fromDate == null || fromDate.trim().isEmpty() ||
                toDate == null || toDate.trim().isEmpty()) {
            return true;
        }

        // "불명확" 또는 "명시되지 않음" 등의 키워드가 포함된 경우
        String[] uncertainKeywords = {"불명확", "명시되지", "확실하지", "애매", "모호", "unclear", "unknown", "ambiguous"};
        for (String keyword : uncertainKeywords) {
            if (fromDate.toLowerCase().contains(keyword.toLowerCase()) ||
                    toDate.toLowerCase().contains(keyword.toLowerCase())) {
                return true;
            }
        }

        // 동일한 날짜가 반복되거나 기본값인 경우 (예: 1970-01-01, 9999-12-31 등)
        if (fromDate.equals(toDate) && (fromDate.equals("1970-01-01") || fromDate.equals("9999-12-31"))) {
            return true;
        }

        return false;
    }

    /**
     * 날짜 명확화 요청 메시지 생성
     */
    private String generateDateClarificationMessage(String userQuestion, Map<String, String> dateInfo) {
        StringBuilder message = new StringBuilder();
        message.append("죄송합니다. 질문에서 날짜 범위를 명확히 파악하기 어렵습니다.\n\n");
        message.append("원하시는 분석 기간을 다음과 같은 형식으로 알려주세요:\n");
        message.append("- '2024년 1월부터 3월까지'\n");
        message.append("- '최근 3개월'\n");
        message.append("- '작년 전체'\n");
        message.append("- '2024년 상반기'\n\n");

        if (dateInfo != null && !dateInfo.isEmpty()) {
            message.append("현재 추출된 날짜 정보:\n");
            message.append("- 시작일: ").append(dateInfo.getOrDefault("from_date", "불명확")).append("\n");
            message.append("- 종료일: ").append(dateInfo.getOrDefault("to_date", "불명확")).append("\n\n");
        }

        message.append("구체적인 기간을 입력해 주시면 정확한 분석을 도와드리겠습니다.");

        return message.toString();
    }
}