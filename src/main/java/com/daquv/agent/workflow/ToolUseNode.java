package com.daquv.agent.workflow;

import com.daquv.agent.quvi.llmadmin.GenerationService;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.LlmOutputHandler;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.util.WebSocketUtils;
import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import com.daquv.agent.workflow.util.DateUtils;
import com.daquv.agent.workflow.util.LLMRequest;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Component
public class ToolUseNode implements WorkflowNode {

    private static final String SQL_TEMPLATE = "SELECT * FROM sql_func('first_param', 'second_param', 'third_param', 'from_date', 'to_date')";
    private static final String JSON_FORMAT = "\"from_date\": from_date, \"to_date\": to_date";

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

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public String getId() {
        return "tooluse";
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

        log.info("=== ToolUse 노드 실행 시작 ===");
        log.info("사용자 질문: {}", userQuestion);

        try {
            // WebSocket 시작 메시지 전송
            webSocketUtils.sendNodeStart(state.getWebSocketSession(), "tooluse");

            // 1단계: 도구/API 선택
            String selectedTool = selectTool(userQuestion, chainId, state);

            if (selectedTool == null || selectedTool.trim().isEmpty()) {
                log.error("도구 선택에 실패했습니다.");
                state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("TOOL_SELECTION_ERROR", "적절한 도구를 선택할 수 없습니다."));
                return;
            }

            log.info("선택된 도구: {}", selectedTool);
            state.setSelectedApi(selectedTool);

            // 2단계: 파라미터 생성
            if (isParameterizedTool(selectedTool)) {
                boolean parameterSuccess = generateParameters(userQuestion, selectedTool, chainId, state);

                if (!parameterSuccess) {
                    log.error("파라미터 생성에 실패했습니다.");
                    state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("PARAMETER_ERROR", "도구 실행을 위한 파라미터 생성에 실패했습니다."));
                    return;
                }
            }

            // 3단계: 도구별 특수 처리
            performToolSpecificProcessing(selectedTool, userQuestion, chainId, state);

            log.info("=== ToolUse 노드 실행 완료 ===");
            log.info("최종 생성된 쿼리/명령: {}", state.getSqlQuery());

            // WebSocket 완료 메시지 전송
            Map<String, Object> data = new HashMap<>();
            data.put("selected_tool", selectedTool);
            data.put("sql_query", state.getSqlQuery());
            webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "tooluse", data);

        } catch (Exception e) {
            log.error("ToolUse 노드 실행 중 예외 발생: {}", e.getMessage(), e);
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("TOOLUSE_ERROR", "도구 사용 중 오류가 발생했습니다."));
        }
    }

    /**
     * 1단계: 사용자 질문을 분석하여 적절한 도구/API 선택
     */
    private String selectTool(String userQuestion, String chainId, WorkflowState state) {
        try {
            log.info("1단계: 도구 선택 시작");

            // QnA ID 생성
            String qnaId = generationService.createQnaId(state.getNodeId());

            // History 조회
            List<Map<String, Object>> toolHistory = promptBuilder.getFunkHistory(chainId);

            // Tool 선택 프롬프트 생성
            PromptBuilder.PromptWithRetrieveTime promptWithTime = promptBuilder.buildFunkPromptWithFewShots(
                    userQuestion, toolHistory, qnaId, chainId);
            PromptTemplate promptTemplate = promptWithTime.getPromptTemplate();
            String prompt = promptTemplate.build();

            log.info("도구 선택 프롬프트 생성 완료");

            // LLM 호출하여 도구 선택
            long startTime = System.currentTimeMillis();
            String llmResponse = llmService.callQwenLlm(prompt, qnaId, chainId);
            long endTime = System.currentTimeMillis();

            // 프로파일링 기록
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordLlmCall(chainId, elapsedTime, "tooluse_select");

            String selectedTool = LlmOutputHandler.extractAnswer(llmResponse);
            selectedTool = LlmOutputHandler.handleAiColon(selectedTool);

            log.info("선택된 도구: {}", selectedTool);
            return selectedTool;

        } catch (Exception e) {
            log.error("도구 선택 중 오류 발생: {}", e.getMessage(), e);
            return null;
        }
    }

    /**
     * 2단계: 선택된 도구에 필요한 파라미터 생성
     */
    private boolean generateParameters(String userQuestion, String selectedTool, String chainId, WorkflowState state) {
        try {
            log.info("2단계: 파라미터 생성 시작 - 도구: {}", selectedTool);

            String companyId = state.getUserInfo().getCompanyId();
            String userId = state.getUserInfo().getUserId();
            String useInttId = state.getUserInfo().getUseInttId();

            // QnA ID 생성
            String qnaId = generationService.createQnaId(state.getNodeId());

            // History 조회
            List<Map<String, Object>> paramsHistory = promptBuilder.getParamsHistory(chainId);

            // 오늘 날짜 정보
            String todayFormatted = DateUtils.getTodayFormatted();
            String todayStr = DateUtils.getTodayStr();
            String todayWithWeekday = DateUtils.formatDateWithWeekday();

            // 사용자 질문 포맷팅
            String formattedQuestion = userQuestion + ", 오늘: " + todayWithWeekday + ".";

            // 파라미터 생성 프롬프트
            PromptBuilder.PromptWithRetrieveTime promptWithTime = promptBuilder.buildParamsPromptWithFewShots(
                    formattedQuestion, paramsHistory, qnaId, todayFormatted, JSON_FORMAT, chainId);
            PromptTemplate promptTemplate = promptWithTime.getPromptTemplate();
            String prompt = promptTemplate.build();

            log.info("파라미터 생성 프롬프트 생성 완료");

            // LLM 호출하여 파라미터 추출
            long startTime = System.currentTimeMillis();
            String llmResponse = llmService.callQwenLlm(prompt, qnaId, chainId);
            long endTime = System.currentTimeMillis();

            // 프로파일링 기록
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordLlmCall(chainId, elapsedTime, "tooluse_params");

            String rawOutput = LlmOutputHandler.extractAnswer(llmResponse);
            rawOutput = LlmOutputHandler.handleAiColon(rawOutput);

            // JSON 파싱
            Map<String, Object> output = parseJsonOutput(rawOutput);

            if (!output.containsKey("from_date") || !output.containsKey("to_date")) {
                log.error("필수 날짜 파라미터가 없습니다: {}", output);
                return false;
            }

            // 날짜 형식 변환 및 검증
            String fromDate = DateUtils.convertDateFormat((String) output.get("from_date"));
            String toDate = DateUtils.convertDateFormat((String) output.get("to_date"));

            // 미래 날짜 교정
            if (DateUtils.isFutureDate(fromDate)) {
                log.warn("미래 from_date: {}, 오늘로 교정: {}", fromDate, todayStr);
                fromDate = todayStr;
                state.setFutureDate(true);
            }

            if (DateUtils.isFutureDate(toDate)) {
                log.warn("미래 to_date: {}, 오늘로 교정: {}", toDate, todayStr);
                toDate = todayStr;
                state.setFutureDate(true);
            }

            // 파라미터 유효성 검사
            if (useInttId == null || userId == null || companyId == null) {
                log.error("필수 사용자 정보가 누락되었습니다.");
                return false;
            }

            // SQL 쿼리 생성
            String sqlQuery = SQL_TEMPLATE
                    .replace("sql_func", selectedTool)
                    .replace("first_param", useInttId)
                    .replace("second_param", userId)
                    .replace("third_param", companyId)
                    .replace("from_date", fromDate)
                    .replace("to_date", toDate);

            // 상태 업데이트
            state.setSqlQuery(sqlQuery.trim());
            state.setStartDate(fromDate);
            state.setEndDate(toDate);

            log.info("파라미터 생성 완료: from_date={}, to_date={}", fromDate, toDate);
            return true;

        } catch (Exception e) {
            log.error("파라미터 생성 중 오류 발생: {}", e.getMessage(), e);
            return false;
        }
    }

    /**
     * 3단계: 도구별 특수 처리 (예: YQMD 분류 등)
     */
    private void performToolSpecificProcessing(String selectedTool, String userQuestion, String chainId, WorkflowState state) {
        log.info("3단계: 도구별 특수 처리 시작 - 도구: {}", selectedTool);

        try {
            switch (selectedTool) {
                case "aicfo_get_financial_flow":
                    // YQMD 처리가 필요한 경우
                    performYqmdProcessing(userQuestion, chainId, state);
                    break;

                case "aicfo_get_balance_sheet":
                    // 대차대조표 관련 특수 처리
                    log.info("대차대조표 API 특수 처리");
                    break;

                case "aicfo_get_income_statement":
                    // 손익계산서 관련 특수 처리
                    log.info("손익계산서 API 특수 처리");
                    break;

                default:
                    // 기본 처리 (특별한 후처리 없음)
                    log.info("기본 도구 처리 완료");
                    break;
            }

        } catch (Exception e) {
            log.error("도구별 특수 처리 중 오류 발생: {}", e.getMessage(), e);
            // 특수 처리 실패는 전체 워크플로우를 중단하지 않음
        }
    }

    /**
     * YQMD 분류 처리 (기존 YqmdNode 로직 통합)
     */
    private void performYqmdProcessing(String userQuestion, String chainId, WorkflowState state) {
        try {
            log.info("YQMD 분류 처리 시작");

            // 벡터 스토어 API 호출 등의 YQMD 분류 로직
            // 여기서는 기본값 'M' 사용
            String yqmdClassification = "M";

            // 현재 SQL 쿼리에 YQMD 파라미터 추가
            String currentQuery = state.getSqlQuery();
            if (currentQuery != null && !currentQuery.trim().isEmpty()) {
                String modifiedQuery = appendYqmdParameter(currentQuery, yqmdClassification);
                state.setSqlQuery(modifiedQuery);

                log.info("YQMD 파라미터 추가 완료: {}", yqmdClassification);
            }

        } catch (Exception e) {
            log.error("YQMD 처리 중 오류 발생: {}", e.getMessage(), e);
        }
    }

    /**
     * 도구가 파라미터가 필요한지 확인
     */
    private boolean isParameterizedTool(String tool) {
        // API 함수들은 대부분 파라미터가 필요
        List<String> parameterizedTools = Arrays.asList(
                "aicfo_get_financial_flow",
                "aicfo_get_balance_sheet",
                "aicfo_get_income_statement",
                "aicfo_get_cash_flow"
        );

        return parameterizedTools.contains(tool);
    }

    /**
     * JSON 출력 파싱
     */
    private Map<String, Object> parseJsonOutput(String rawOutput) throws Exception {
        try {
            return objectMapper.readValue(rawOutput, new TypeReference<Map<String, Object>>() {});
        } catch (Exception jsonError) {
            // 텍스트에서 JSON 형식 찾기
            Pattern jsonPattern = Pattern.compile("\\{.*?\\}", Pattern.DOTALL);
            Matcher matcher = jsonPattern.matcher(rawOutput);

            if (matcher.find()) {
                String jsonStr = matcher.group(0);
                return objectMapper.readValue(jsonStr, new TypeReference<Map<String, Object>>() {});
            } else {
                throw new IllegalArgumentException("JSON 형식을 찾을 수 없습니다: " + rawOutput);
            }
        }
    }

    /**
     * SQL 쿼리에 YQMD 파라미터 추가
     */
    private String appendYqmdParameter(String sqlQuery, String yqmdValue) {
        String trimmedQuery = sqlQuery.trim();
        if (trimmedQuery.endsWith(")")) {
            int lastParenIndex = trimmedQuery.lastIndexOf(')');
            return trimmedQuery.substring(0, lastParenIndex) + String.format(", '%s')", yqmdValue);
        } else {
            log.warn("쿼리가 ')'로 끝나지 않아 YQMD 파라미터를 추가할 수 없습니다. 원본 쿼리를 반환합니다.");
            return sqlQuery;
        }
    }
}