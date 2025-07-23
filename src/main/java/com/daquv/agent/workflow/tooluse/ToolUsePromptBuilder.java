package com.daquv.agent.workflow.tooluse;

import com.daquv.agent.quvi.llmadmin.GenerationService;
import com.daquv.agent.quvi.llmadmin.HistoryService;
import com.daquv.agent.quvi.requests.VectorRequest;
import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

@Component
@Slf4j
public class ToolUsePromptBuilder {

    @Autowired
    private PromptBuilder promptBuilder;

    @Autowired
    private HistoryService historyService;

    @Autowired
    private GenerationService generationService;

    @Autowired
    private VectorRequest vectorRequest;

    /**
     * Funk 노드용 history 조회 및 변환
     */
    public List<Map<String, Object>> getFunkHistory(String chainId) {
        List<String> requiredFields = Arrays.asList("user_question", "selected_api");
        Map<String, List<Map<String, Object>>> historyDict = historyService.getHistory(chainId, requiredFields, "funk", 5);
        return promptBuilder.convertToChatHistory(historyDict, requiredFields, "user_question", "selected_api");
    }

    /**
     * Funk 프롬프트 생성 (few-shot 포함, QnA 저장)
     */
    public PromptBuilder.PromptWithRetrieveTime buildFunkPromptWithFewShots(String userQuestion, List<Map<String, Object>> funkHistory, String qnaId, String chainId) {
        try {
            // Few-shot 예제 검색
            Map<String, Object> fewShotResult = vectorRequest.getFewShots(userQuestion, "shots_api_selector", 5, chainId);

            @SuppressWarnings("unchecked")
            List<Map<String, Object>> fewShots = (List<Map<String, Object>>) fewShotResult.get("few_shots");
            BigDecimal retrieveTime = BigDecimal.valueOf((Double) fewShotResult.getOrDefault("retrieve_time", 0.0));

            // 기본 시스템 프롬프트 로드
            PromptTemplate template = PromptTemplate.fromFile("funk");
            String systemPrompt = template.replace("{today}", LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd")));

            // Few-shot 예제 QnA 저장
            if (qnaId != null && fewShots != null) {
                for (int i = 0; i < fewShots.size(); i++) {
                    Map<String, Object> shot = fewShots.get(i);
                    String input = (String) shot.get("input");
                    String output = (String) shot.get("output");

                    if (input != null && output != null) {
                        generationService.recordFewshot(qnaId, input, input, output, i + 1);
                    }
                }
            }

            // 프롬프트 구성
            PromptTemplate finalTemplate = PromptTemplate.from("")
                    .withSystemPrompt(systemPrompt)
                    .withFewShots(fewShots)
                    .withHistory(funkHistory)
                    .withUserMessage(userQuestion);

            return new PromptBuilder.PromptWithRetrieveTime(finalTemplate, retrieveTime);

        } catch (Exception e) {
            log.error("Funk 프롬프트 생성 중 오류 발생: {}", e.getMessage(), e);

            // 오류 발생 시 기본 프롬프트 반환
            PromptTemplate template = PromptTemplate.fromFile("funk");
            String systemPrompt = template.replace("{today}", LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd")));

            PromptTemplate finalTemplate = PromptTemplate.from("")
                    .withSystemPrompt(systemPrompt)
                    .withHistory(funkHistory)
                    .withUserMessage(userQuestion);

            return new PromptBuilder.PromptWithRetrieveTime(finalTemplate, BigDecimal.ZERO);
        }
    }


    /**
     * Params 노드용 history 조회 및 변환
     */
    public List<Map<String, Object>> getParamsHistory(String chainId) {
        List<String> requiredFields = Arrays.asList("user_question", "date_info");
        Map<String, List<Map<String, Object>>> historyDict = historyService.getHistory(chainId, requiredFields, "params", 5);
        return promptBuilder.convertToChatHistory(historyDict, requiredFields, "user_question", "date_info");
    }

    /**
     * Params 프롬프트 생성 (few-shot 포함)
     */
    public PromptBuilder.PromptWithRetrieveTime buildParamsPromptWithFewShots(String userQuestion, List<Map<String, Object>> paramsHistory, String qnaId, String todayFormatted, String jsonFormat, String chainId) {
        try {
            // Few-shot 예제 검색
            Map<String, Object> fewShotResult = vectorRequest.getFewShots(userQuestion, "shots_params_creator", 5, chainId);

            @SuppressWarnings("unchecked")
            List<Map<String, Object>> fewShots = (List<Map<String, Object>>) fewShotResult.get("few_shots");
            BigDecimal retrieveTime = BigDecimal.valueOf((Double) fewShotResult.getOrDefault("retrieve_time", 0.0));

            // 기본 시스템 프롬프트 로드
            PromptTemplate template = PromptTemplate.fromFile("params");
            String systemPrompt = template.replace("{today}", todayFormatted)
                    .replace("{json_format}", jsonFormat);

            // Few-shot 예제 처리 및 QnA 저장
            if (qnaId != null && fewShots != null) {
                for (int i = 0; i < fewShots.size(); i++) {
                    Map<String, Object> shot = fewShots.get(i);
                    String input = (String) shot.get("input");
                    String output = (String) shot.get("output");
                    String date = (String) shot.get("date");

                    if (input != null && output != null) {
                        // 날짜 정보가 있으면 추가
                        String humanWithDate = date != null ? input + ", 오늘: " + date + "." : input;
                        String formattedOutput = "{" + output + "}";

                        generationService.recordFewshot(qnaId, input, humanWithDate, formattedOutput, i + 1);
                    }
                }
            }

            // 프롬프트 구성
            PromptTemplate finalTemplate = PromptTemplate.from("")
                    .withSystemPrompt(systemPrompt)
                    .withFewShots(fewShots)
                    .withHistory(paramsHistory)
                    .withUserMessage(userQuestion);

            return new PromptBuilder.PromptWithRetrieveTime(finalTemplate, retrieveTime);

        } catch (Exception e) {
            log.error("Params 프롬프트 생성 중 오류 발생: {}", e.getMessage(), e);

            // 오류 발생 시 기본 프롬프트 반환
            PromptTemplate template = PromptTemplate.fromFile("params");
            String systemPrompt = template.replace("{today}", todayFormatted)
                    .replace("{json_format}", jsonFormat);

            PromptTemplate finalTemplate = PromptTemplate.from("")
                    .withSystemPrompt(systemPrompt)
                    .withHistory(paramsHistory)
                    .withUserMessage(userQuestion);

            return new PromptBuilder.PromptWithRetrieveTime(finalTemplate, BigDecimal.ZERO);
        }
    }
}
