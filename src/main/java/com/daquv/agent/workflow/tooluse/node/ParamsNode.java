package com.daquv.agent.workflow.tooluse.node;

import com.daquv.agent.quvi.llmadmin.GenerationService;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.LlmOutputHandler;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import com.daquv.agent.workflow.tooluse.ToolUsePromptBuilder;
import com.daquv.agent.workflow.tooluse.ToolUseWorkflowNode;
import com.daquv.agent.workflow.tooluse.ToolUseWorkflowState;
import com.daquv.agent.workflow.util.LLMRequest;
import com.daquv.agent.quvi.util.WebSocketUtils;
import com.daquv.agent.workflow.util.DateUtils;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Component
public class ParamsNode implements ToolUseWorkflowNode {

    /**
     * Python의 parameters 함수와 동일한 기능을 수행하는 Java 구현
     * - 사용자 질문에서 날짜 파라미터를 추출
     * - Few-shot 학습 기반으로 정확한 날짜 범위 결정
     * - SQL 쿼리 템플릿에 파라미터 삽입하여 실행 가능한 쿼리 생성
     */

    private static final String SQL_TEMPLATE = "SELECT * FROM sql_func('first_param', 'second_param', 'third_param', 'from_date', 'to_date')";
    private static final String JSON_FORMAT = "\"from_date\": from_date, \"to_date\": to_date";

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

    // DateUtils는 static 메서드로 사용

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public String getId() {
        return "params";
    }

    @Override
    public void execute(ToolUseWorkflowState state) {
        String selectedApi = state.getSelectedApi();
        String userQuestion = state.getUserQuestion();
        String companyId = state.getUserInfo().getCompanyId();
        String userId = state.getUserInfo().getUserId();
        String useInttId = state.getUserInfo().getUseInttId();
        String workflowId = state.getWorkflowId();

        if (selectedApi == null || selectedApi.trim().isEmpty()) {
            log.error("선택된 API가 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "선택된 API가 없습니다."));
            return;
        }

        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("사용자 질문이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다."));
            return;
        }

        log.info("API '{}' 파라미터 생성 중, 질문: '{}'", selectedApi, userQuestion.substring(0, Math.min(userQuestion.length(), 50)) + "...");

        try {
            // WebSocket 메시지 전송
            webSocketUtils.sendNodeStart(state.getWebSocketSession(), "params");

            // QnA ID 생성
            String qnaId = generationService.createQnaId(state.getNodeId());

            // History 조회
            List<Map<String, Object>> paramsHistory = promptBuilder.getParamsHistory(workflowId);

            // 오늘 날짜 포맷팅
            String todayFormatted = DateUtils.getTodayFormatted();
            String todayStr = DateUtils.getTodayStr();
            String todayWithWeekday = DateUtils.formatDateWithWeekday();

            // 사용자 질문 포맷팅 (Python의 formatted_question과 동일)
            String formattedQuestion = userQuestion + ", 오늘: " + todayWithWeekday + ".";

            // Params 프롬프트 생성 (Few-shot 및 QnA 포함)
            PromptBuilder.PromptWithRetrieveTime promptWithTime = promptBuilder.buildParamsPromptWithFewShots(
                    formattedQuestion, paramsHistory, qnaId, todayFormatted, JSON_FORMAT, workflowId);
            PromptTemplate promptTemplate = promptWithTime.getPromptTemplate();
            String prompt = promptTemplate.build();

            // 질문 기록
            log.info("===== params(Q) =====");

            // LLM 호출하여 날짜 파라미터 추출 with 프로파일링
            long startTime = System.currentTimeMillis();
            String llmResponse = llmService.callQwenLlm(prompt, qnaId, workflowId);
            long endTime = System.currentTimeMillis();

            // LLM 프로파일링 기록
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordLlmCall(workflowId, elapsedTime, "params");

            String rawOutput = LlmOutputHandler.extractAnswer(llmResponse);

            // "ai:" 접두사 제거
            rawOutput = LlmOutputHandler.handleAiColon(rawOutput);

            // JSON 파싱
            Map<String, Object> output = parseJsonOutput(rawOutput);

            // 필수 키 확인
            if (!output.containsKey("from_date") || !output.containsKey("to_date")) {
                throw new IllegalArgumentException("응답에 (from_date, to_date)가 없어요..: " + output);
            }

            log.info("추출된 파라미터: from_date={}, to_date={}", output.get("from_date"), output.get("to_date"));

            // 날짜 형식 변환
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

            // SQL 쿼리 생성 전에 null 체크 추가
            if (useInttId == null || userId == null || companyId == null || fromDate == null || toDate == null) {
                log.error("필수 파라미터가 null입니다: useInttId={}, userId={}, companyId={}, fromDate={}, toDate={}",
                        useInttId, userId, companyId, fromDate, toDate);
            }

            log.info("최종 파라미터: from_date={}, to_date={}", fromDate, toDate);
            log.info("1---------------");

            // SQL 쿼리 생성
            String sqlQuery = SQL_TEMPLATE
                    .replace("sql_func", selectedApi)
                    .replace("first_param", useInttId)
                    .replace("second_param", userId)
                    .replace("third_param", companyId)
                    .replace("from_date", fromDate)
                    .replace("to_date", toDate);
            log.info("2---------------");
            // 답변 기록
            log.info("===== params(A) =====");
            log.info("생성된 SQL 쿼리: {}", sqlQuery);
            log.info("3---------------");

            // 상태 업데이트
            state.setSqlQuery(sqlQuery.trim());
            state.setStartDate(fromDate);
            state.setEndDate(toDate);
            log.info("4---------------");

            log.info("파라미터 생성 완료");

        } catch (Exception e) {
            log.error("ParamsNode 실행 중 예외 발생: {}", e.getMessage(), e);
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("PARAMS_ERROR", "파라미터 생성 중 오류가 발생했습니다."));
        }
    }

    /**
     * JSON 출력 파싱
     */
    private Map<String, Object> parseJsonOutput(String rawOutput) throws Exception {
        try {
            // 첫 번째 시도: 직접 JSON 파싱
            return objectMapper.readValue(rawOutput, new TypeReference<Map<String, Object>>() {});
        } catch (Exception jsonError) {
            // 두 번째 시도: 텍스트에서 JSON 형식 찾기
            Pattern jsonPattern = Pattern.compile("\\{.*?\\}", Pattern.DOTALL);
            Matcher matcher = jsonPattern.matcher(rawOutput);

            if (matcher.find()) {
                try {
                    String jsonStr = matcher.group(0);
                    return objectMapper.readValue(jsonStr, new TypeReference<Map<String, Object>>() {});
                } catch (Exception parseError) {
                    throw new IllegalArgumentException("JSON이 있는 거 같은데 파싱이 어려워요..: " + rawOutput);
                }
            } else {
                throw new IllegalArgumentException("JSON이 없어요..: " + rawOutput);
            }
        }
    }
}