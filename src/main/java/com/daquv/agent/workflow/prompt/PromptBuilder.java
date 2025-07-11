package com.daquv.agent.workflow.prompt;

import com.daquv.agent.quvi.llmadmin.QnaService;
import com.daquv.agent.quvi.llmadmin.HistoryService;
import com.daquv.agent.quvi.requests.VectorRequest;
import com.daquv.agent.workflow.util.DateUtils;
import lombok.Getter;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Slf4j
@Component
public class PromptBuilder {

    @Autowired
    private VectorRequest vectorRequest;
    
    @Autowired
    private QnaService qnaService;
    
    @Autowired
    private HistoryService historyService;

    @Getter
    public static class PromptWithRetrieveTime {
        private final PromptTemplate promptTemplate;
        private final BigDecimal retrieveTime;

        PromptWithRetrieveTime(PromptTemplate promptTemplate, BigDecimal retrieveTime) {
            this.promptTemplate = promptTemplate;
            this.retrieveTime = retrieveTime;
        }
    }
    
    // Commander 프롬프트 생성 및 RetrieveTime 반환 (few-shot 포함 + QnA 저장)
    public PromptWithRetrieveTime buildCommanderPromptWithFewShots(String userQuestion, String qnaId) {
        // 기본 시스템 프롬프트 로드
        PromptTemplate template = PromptTemplate.fromFile("commander");
        String systemPrompt = template.replace("{user_question}", userQuestion);
        
        // Few-shot 예제 검색
        Map<String, Object> fewShotResult = vectorRequest.getFewShots(
            userQuestion, "shots_selector", 5, null);
        
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> fewShots = (List<Map<String, Object>>) fewShotResult.get("few_shots");

        List<Map<String, Object>> reversedFewShots = new ArrayList<>();
        if (fewShots != null) {
            for (int i = fewShots.size() - 1; i >= 0; i--) {
                reversedFewShots.add(fewShots.get(i));
            }
        }

        BigDecimal lastRetrieveTimeFromResults = BigDecimal.ZERO;

        // QnA ID가 있으면 few-shot 저장
        if (qnaId != null && reversedFewShots != null) {
            for (int i = 0; i < reversedFewShots.size(); i++) {
                Map<String, Object> shot = reversedFewShots.get(i);
                String input = (String) shot.get("input");
                String output = (String) shot.get("output");
                Object retrieveTimeObj = shot.getOrDefault("retrieve_time", 0.0);
                if (retrieveTimeObj instanceof Double) {
                    lastRetrieveTimeFromResults = BigDecimal.valueOf((Double) retrieveTimeObj);
                } else if (retrieveTimeObj instanceof BigDecimal) {
                    lastRetrieveTimeFromResults = (BigDecimal) retrieveTimeObj;
                } else if (retrieveTimeObj instanceof Number) {
                    lastRetrieveTimeFromResults = BigDecimal.valueOf(((Number) retrieveTimeObj).doubleValue());
                }
                if (input != null && output != null) {
                    qnaService.recordFewshot(qnaId, input, input, output, i + 1);
                }
            }
        }
        
        // 프롬프트 구성
        PromptTemplate result = PromptTemplate.from("")
                .withSystemPrompt(systemPrompt)
                .withFewShotsWithoutDateModification(reversedFewShots)
                .withUserMessage(userQuestion);

        return new PromptWithRetrieveTime(result, lastRetrieveTimeFromResults);
    }

    // Dater 프롬프트 생성 및 RetrieveTime 반환
    public PromptWithRetrieveTime buildDaterPromptWithFewShots(String selectedTable, String userQuestion,
                                                       List<Map<String, Object>> daterHistory, String qnaId) {
        String today = DateUtils.getTodayDash();
        String jsonFormat = "\"from_date\": from_date, \"to_date\": to_date";

        // 테이블별 프롬프트 선택
        PromptTemplate template;
        if ("amt".equals(selectedTable) || "stock".equals(selectedTable)) {
            template = PromptTemplate.fromFile("date-amt");
        } else if ("trsc".equals(selectedTable)) {
            template = PromptTemplate.fromFile("date-trsc");
        } else {
            // 기본값으로 amt 사용
            template = PromptTemplate.fromFile("date-amt");
        }

        String systemPrompt = template.replaceAll(
                "{today}", today,
                "{json_format}", jsonFormat
        );

        // Few-shot 예제 검색
        Map<String, Object> fewShotResult = vectorRequest.getFewShots(
                userQuestion, "shots_params_creator", 5, null);

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> fewShots = (List<Map<String, Object>>) fewShotResult.get("few_shots");

        List<Map<String, Object>> reversedFewShots = new ArrayList<>();
        if (fewShots != null) {
            for (int i = fewShots.size() - 1; i >= 0; i--) {
                reversedFewShots.add(fewShots.get(i));
            }
        }

        BigDecimal lastRetrieveTimeFromResults = BigDecimal.ZERO;

        // QnA ID가 있으면 few-shot 저장
        if (qnaId != null && reversedFewShots != null) {
            for (int i = 0; i < reversedFewShots.size(); i++) {
                Map<String, Object> shot = reversedFewShots.get(i);
                String input = (String) shot.get("input");
                String output = (String) shot.get("output");

                Object retrieveTimeObj = shot.getOrDefault("retrieve_time", 0.0);
                if (retrieveTimeObj instanceof Double) {
                    lastRetrieveTimeFromResults = BigDecimal.valueOf((Double) retrieveTimeObj);
                } else if (retrieveTimeObj instanceof BigDecimal) {
                    lastRetrieveTimeFromResults = (BigDecimal) retrieveTimeObj;
                } else if (retrieveTimeObj instanceof Number) {
                    lastRetrieveTimeFromResults = BigDecimal.valueOf(((Number) retrieveTimeObj).doubleValue());
                }

                if (input != null && output != null) {

                    String humanWithDate = input;
                    if (shot.containsKey("date")) {
                        String date = (String) shot.get("date");
                        humanWithDate = input + ", 오늘: " + date + ".";
                    }

                    String formattedOutput = "{" + output + "}";

                    qnaService.recordFewshot(qnaId, input, humanWithDate, formattedOutput, i + 1);
                }
            }
        }

        // 사용자 질문 포맷팅 (날짜 정보 포함)
        String formattedQuestion = DateUtils.formatQuestionWithDate(userQuestion);

        PromptTemplate result = PromptTemplate.from("")
                .withSystemPrompt(systemPrompt)
                .withFewShotsForDater(reversedFewShots)  // 날짜 추가하여 처리
                .withHistory(daterHistory)
                .withUserMessage(formattedQuestion);

        return new PromptWithRetrieveTime(result, lastRetrieveTimeFromResults);
    }

    public PromptTemplate buildNL2SQLPrompt(String questionWithError) {
        String today = DateUtils.getTodayFormatted();

        PromptTemplate template = PromptTemplate.fromFile("nl2sql");
        String systemPrompt = template.replaceAll(
                "{user_question}", questionWithError,
                "{today}", today
        );

        return PromptTemplate.from("").withSystemPrompt(systemPrompt);
    }

    // NL2SQL 프롬프트 생성 (few-shot + history + QnA 저장 포함)
    public PromptWithRetrieveTime buildNL2SQLPromptWithFewShotsAndHistory(
            String targetTable, String userQuestion, List<Map<String, Object>> nl2sqlHistory,
            String qnaId, String companyId, String startDate, String endDate
    ) {
        String dateInfoStr = String.format("(%s, %s)", startDate, endDate);
        
        // 기본 시스템 프롬프트 로드
        PromptTemplate template = PromptTemplate.fromFile("nl2sql-" + targetTable.toLowerCase());
        String systemPrompt = template.replaceAll(
            "{main_com}", companyId,
            "{date_info}", dateInfoStr
        );
        
        // Few-shot 예제 검색
        Map<String, Object> fewShotResult = vectorRequest.getFewShots(
            userQuestion, "shots_" + targetTable.toLowerCase(), 3, null);
        
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> fewShots = (List<Map<String, Object>>) fewShotResult.get("few_shots");

        BigDecimal lastRetrieveTimeFromResults = BigDecimal.ZERO;
        
        // QnA ID가 있으면 few-shot 저장
        List<Map<String, Object>> processedFewShots = new java.util.ArrayList<>();
        if (fewShots != null) {
            for (int i = 0; i < fewShots.size(); i++) {
                Map<String, Object> shot = fewShots.get(i);
                String input = (String) shot.get("input");
                String output = (String) shot.get("output");
                Object retrieveTimeObj = shot.getOrDefault("retrieve_time", 0.0);
                if (retrieveTimeObj instanceof Double) {
                    lastRetrieveTimeFromResults = BigDecimal.valueOf((Double) retrieveTimeObj);
                } else if (retrieveTimeObj instanceof BigDecimal) {
                    lastRetrieveTimeFromResults = (BigDecimal) retrieveTimeObj;
                } else if (retrieveTimeObj instanceof Number) {
                    lastRetrieveTimeFromResults = BigDecimal.valueOf(((Number) retrieveTimeObj).doubleValue());
                }
                if (input != null && output != null) {
                    // 날짜 정보가 있으면 질문에 추가
                    String humanWithDate = input;
                    if (shot.containsKey("date")) {
                        String date = (String) shot.get("date");
                        humanWithDate = input + ", 오늘: " + date + ".";
                    }
                    qnaService.recordFewshot(qnaId, input, humanWithDate, output, i + 1);

                    // 변환된 few-shot을 새 리스트에 추가
                    Map<String, Object> processedShot = new HashMap<>(shot);
                    processedShot.put("input", humanWithDate);
                    processedFewShots.add(processedShot);
                }
            }
        }
        
        // 사용자 질문 포맷팅 (날짜 정보 포함)
        String formattedQuestion = DateUtils.formatQuestionWithDate(userQuestion);
        
        // 프롬프트 구성
        PromptTemplate promptTemplate = PromptTemplate.from("")
                .withSystemPrompt(systemPrompt)
                .withFewShots(processedFewShots)
                .withHistory(nl2sqlHistory)
                .withUserMessage(formattedQuestion);

        return new PromptWithRetrieveTime(promptTemplate, lastRetrieveTimeFromResults);
    }

    // Respondent 프롬프트 생성 (few-shot + history + QnA 저장 포함)
    public PromptWithRetrieveTime buildRespondentPromptWithFewShotsAndHistory(
            String userQuestion, String tablePipe, List<Map<String, Object>> respondentHistory, String qnaId,
            Boolean isApi, String startDate, String endDate
    ) {
        try {
            // 기본 시스템 프롬프트 로드
            PromptTemplate template = PromptTemplate.fromFile("respondent");
            String systemPrompt = template.build();

            // API 질의와 SQL 질의에 따라 다른 퓨샷 컬렉션 사용
            String collectionName = isApi ? "shots_respondent_api" : "shots_respondent_table";

            // Few-shot 예제 검색
            Map<String, Object> fewShotResult = vectorRequest.getFewShots(
                    userQuestion, collectionName, 5, null);

            @SuppressWarnings("unchecked")
            List<Map<String, Object>> fewShots = (List<Map<String, Object>>) fewShotResult.get("few_shots");
            BigDecimal retrieveTime = BigDecimal.valueOf((Double) fewShotResult.getOrDefault("retrieve_time", 0.0));

            // 날짜 정보를 포함한 사용자 질문 포맷팅
            String formattedUserQuestion = userQuestion;
            if (startDate != null && endDate != null && !startDate.isEmpty() && !endDate.isEmpty()) {
                try {
                    // 날짜 포맷팅 (YYYYMMDD -> YYYY년 MM월 DD일)
                    String formattedFromDate = null;
                    String formattedToDate = null;

                    if (startDate.length() >= 8) {
                        String normalizedStartDate = DateUtils.convertDateFormat(startDate);
                        LocalDate fromDate = LocalDate.parse(normalizedStartDate, DateTimeFormatter.ofPattern("yyyyMMdd"));
                        formattedFromDate = fromDate.format(DateTimeFormatter.ofPattern("yyyy년 MM월 dd일"));
                    }

                    if (endDate.length() >= 8) {
                        String normalizedEndDate = DateUtils.convertDateFormat(endDate);
                        LocalDate toDate = LocalDate.parse(normalizedEndDate, DateTimeFormatter.ofPattern("yyyyMMdd"));
                        formattedToDate = toDate.format(DateTimeFormatter.ofPattern("yyyy년 MM월 dd일"));
                    }

                    if (formattedFromDate != null && formattedToDate != null) {
                        formattedUserQuestion = String.format("시작 시점: %s, 종료 시점: %s. %s",
                                formattedFromDate, formattedToDate, userQuestion);
                    }
                } catch (Exception e) {
                    log.warn("Failed to format date info: {}", e.getMessage());
                }
            }

            // 현재 사용자의 human 메시지 구성 (respondent_human 프롬프트 사용)
            PromptTemplate humanTemplate = PromptTemplate.fromFile("respondent_human");
            String humanPrompt = humanTemplate.replaceAll(
                    "{table_pipe}", tablePipe,
                    "{user_question}", formattedUserQuestion
            );

            // Few-shot 예제 역순 처리 (파이썬의 reversed() 구현)
            List<Map<String, Object>> reversedFewShots = new ArrayList<>();
            if (fewShots != null) {
                for (int i = fewShots.size() - 1; i >= 0; i--) {
                    reversedFewShots.add(fewShots.get(i));
                }
            }

            // QnA ID가 있으면 few-shot 저장
            List<Map<String, Object>> processedFewShots = new java.util.ArrayList<>();
            if (fewShots != null) {
                for (int i = 0; i < reversedFewShots.size(); i++) {
                    Map<String, Object> example = reversedFewShots.get(i);
                    String input = (String) example.get("input");
                    String output = (String) example.get("output");

                    if (input != null && output != null) {
                        // Few-shot 예제의 human 메시지 구성
                        String humanWithStats = input;
                        if (example.containsKey("stats")) {
                            String stats = (String) example.get("stats");
                            if (example.containsKey("date")) {
                                String date = (String) example.get("date");
                                humanWithStats = String.format("결과 데이터:\n%s\n\n사용자의 질문:\n%s. %s", stats, date, input);
                            } else {
                                humanWithStats = String.format("결과 데이터:\n%s\n\n사용자의 질문:\n%s", stats, input);
                            }
                        }
                        qnaService.recordFewshot(qnaId, input, humanWithStats, output, i + 1);

                        // 변환된 few-shot을 새 리스트에 추가
                        Map<String, Object> processedShot = new HashMap<>(example);
                        processedShot.put("input", humanWithStats);
                        processedFewShots.add(processedShot);
                    }
                }
            }

            // 히스토리 유효성 검사를 위한 필터링
            List<Map<String, Object>> validHistory = new ArrayList<>();
            if (respondentHistory != null) {
                for (Map<String, Object> historyItem : respondentHistory) {
                    // 히스토리 아이템 유효성 검사 (파이썬의 all() 조건 구현)
                    String[] requiredKeys = {"user_question", "table_pipe", "fstring_answer"};
                    boolean isValid = true;

                    for (String key : requiredKeys) {
                        if (!historyItem.containsKey(key) ||
                                historyItem.get(key) == null ||
                                historyItem.get(key).toString().trim().isEmpty()) {
                            isValid = false;
                            break;
                        }
                    }

                    if (isValid) {
                        validHistory.add(historyItem);
                    }
                }
            }

            // 프롬프트 구성 (기존 코드 스타일 따라 체이닝 방식 사용)
            PromptTemplate finalTemplate = PromptTemplate.from("")
                    .withSystemPrompt(systemPrompt)
                    .withFewShots(processedFewShots)
                    .withHistory(validHistory)
                    .withUserMessage(humanPrompt);

            return new PromptWithRetrieveTime(finalTemplate, retrieveTime);

        } catch (Exception e) {
            log.error("Respondent 프롬프트 생성 중 오류 발생: {}", e.getMessage(), e);

            // 오류 발생 시 기본 프롬프트 반환
            PromptTemplate template = PromptTemplate.fromFile("respondent");
            String systemPrompt = template.build();

            PromptTemplate finalTemplate = PromptTemplate.from("")
                    .withSystemPrompt(systemPrompt)
                    .withUserMessage(userQuestion);

            return new PromptWithRetrieveTime(finalTemplate, BigDecimal.ZERO);
        }
    }

    // Nodata 프롬프트 생성 (history 포함)
    public PromptTemplate buildNodataPromptWithHistory(String userQuestion, List<Map<String, Object>> nodataHistory) {
        PromptTemplate template = PromptTemplate.fromFile("nodata");
        String systemPrompt = template.replace("{user_question}", userQuestion);
        
        // 프롬프트 구성
        return PromptTemplate.from("")
            .withSystemPrompt(systemPrompt)
            .withHistory(nodataHistory)
            .withUserMessage(userQuestion);
    }

    // Killjoy 프롬프트 생성 (상품권 외 질문 차단)
    public PromptTemplate buildKilljoyPrompt(String userQuestion) {
        PromptTemplate template = PromptTemplate.fromFile("killjoy");
        String prompt = template.replace("{user_question}", userQuestion);
        return PromptTemplate.from(prompt);
    }

    // Killjoy 프롬프트 생성 (history 포함)
    public PromptTemplate buildKilljoyPromptWithHistory(String userQuestion, List<Map<String, Object>> killjoyHistory) {
        PromptTemplate template = PromptTemplate.fromFile("killjoy");
        String systemPrompt = template.replace("{user_question}", userQuestion);
        
        // 프롬프트 구성
        return PromptTemplate.from("")
            .withSystemPrompt(systemPrompt)
            .withHistory(killjoyHistory)
            .withUserMessage(userQuestion);
    }

    // Safeguard 프롬프트 생성 (SQL 에러 수정)
    public PromptTemplate buildSafeguardPrompt(String userQuestion, String unsafeQuery, String sqlError) {
        String today = DateUtils.getTodayFormatted();

        PromptTemplate template = PromptTemplate.fromFile("safeguard");

        String prompt = template.replaceAll(
            "{user_question}", userQuestion,
            "{today}", today,
            "{unsafe_query}", unsafeQuery,
            "{sql_error}", sqlError != null ? sqlError : ""
        );

        return PromptTemplate.from("")
                .withSystemPrompt(prompt);
    }

    // 유틸리티: Chat history 변환 (노드별 필드 매핑 지원)
    private List<Map<String, Object>> convertToChatHistory(Map<String, List<Map<String, Object>>> historyDict,
                                                          List<String> requiredFields,
                                                          String humanField,
                                                          String aiField) {
        List<Map<String, Object>> chatHistory = new java.util.ArrayList<>();
        
        if (historyDict == null) {
            return chatHistory;
        }
        
        for (List<Map<String, Object>> historyList : historyDict.values()) {
            for (Map<String, Object> historyItem : historyList) {
                // 모든 필수 필드가 존재하고 None이 아닌 경우에만 추가
                boolean allFieldsPresent = requiredFields.stream()
                    .allMatch(field -> historyItem.containsKey(field) && historyItem.get(field) != null);
                
                if (allFieldsPresent) {
                    Object humanValue = historyItem.get(humanField);
                    Object aiValue = historyItem.get(aiField);
                    
                    // null 체크 추가
                    if (humanValue != null && aiValue != null) {
                        Map<String, Object> historyEntry = new HashMap<>();
                        historyEntry.put("user_question", humanValue);
                        historyEntry.put("final_answer", aiValue);
                        chatHistory.add(historyEntry);
                    }
                }
            }
        }
        
        return chatHistory;
    }

    // History 관련 메서드들

    public List<Map<String, Object>> getDaterHistory(String chainId) {
        List<String> requiredFields = Arrays.asList("user_question", "date_info");
        Map<String, List<Map<String, Object>>> historyDict = historyService.getHistory(chainId, requiredFields, "dater", 5);
        return convertToChatHistory(historyDict, requiredFields, "user_question", "date_info");
    }

    /**
     * NL2SQL 노드용 history 조회 및 변환
     */
    public List<Map<String, Object>> getNl2sqlHistory(String chainId) {
        List<String> requiredFields = Arrays.asList("user_question", "sql_query");
        Map<String, List<Map<String, Object>>> historyDict = historyService.getHistory(chainId, requiredFields, "nl2sql", 5);
        return convertToChatHistory(historyDict, requiredFields, "user_question", "sql_query");
    }

    /**
     * Respondent 노드용 history 조회 및 변환
     */
    public List<Map<String, Object>> getRespondentHistory(String chainId) {
        List<String> requiredFields = Arrays.asList("user_question", "table_pipe", "fstring_answer", "final_answer");
        Map<String, List<Map<String, Object>>> historyDict = historyService.getHistory(chainId, requiredFields, "respondent", 5);
        return convertToChatHistory(historyDict, requiredFields, "user_question", "final_answer");
    }

    /**
     * Nodata 노드용 history 조회 및 변환
     */
    public List<Map<String, Object>> getNodataHistory(String chainId) {
        List<String> requiredFields = Arrays.asList("user_question", "final_answer");
        Map<String, List<Map<String, Object>>> historyDict = historyService.getHistory(chainId, requiredFields, "nodata", 5);
        return convertToChatHistory(historyDict, requiredFields, "user_question", "final_answer");
    }

    /**
     * Killjoy 노드용 history 조회 및 변환
     */
    public List<Map<String, Object>> getKilljoyHistory(String chainId) {
        List<String> requiredFields = Arrays.asList("user_question", "final_answer");
        Map<String, List<Map<String, Object>>> historyDict = historyService.getHistory(chainId, requiredFields, "killjoy", 5);
        return convertToChatHistory(historyDict, requiredFields, "user_question", "final_answer");
    }

    /**
     * 일반적인 history 조회 및 변환 (필드명 지정 가능)
     */
    public List<Map<String, Object>> getHistory(String chainId, List<String> requiredFields, String nodeType, int limit) {
        Map<String, List<Map<String, Object>>> historyDict = historyService.getHistory(chainId, requiredFields, nodeType, limit);
        return convertToChatHistory(historyDict, requiredFields, "user_question", "final_answer");
    }

    // Page Respondent 프롬프트 생성 (페이지네이션 응답)
    public PromptTemplate buildPageRespondentPrompt(String userQuestion, Integer totalRows, List<Map<String, Object>> respondentHistory, String qnaId) {
        // 기본 시스템 프롬프트 로드
        PromptTemplate template = PromptTemplate.fromFile("page-respondent");
        String systemPrompt = template.replace("{total_rows}", String.valueOf(totalRows));
        
        // 프롬프트 구성
        return PromptTemplate.from("")
            .withSystemPrompt(systemPrompt)
            .withHistory(respondentHistory)
            .withUserMessage(userQuestion);
    }

    /**
     * Funk 노드용 history 조회 및 변환
     */
    public List<Map<String, Object>> getFunkHistory(String chainId) {
        List<String> requiredFields = Arrays.asList("user_question", "selected_api");
        Map<String, List<Map<String, Object>>> historyDict = historyService.getHistory(chainId, requiredFields, "funk", 5);
        return convertToChatHistory(historyDict, requiredFields, "user_question", "selected_api");
    }
    
    /**
     * Funk 프롬프트 생성 (few-shot 포함, QnA 저장)
     */
    public PromptWithRetrieveTime buildFunkPromptWithFewShots(String userQuestion, List<Map<String, Object>> funkHistory, String qnaId) {
        try {
            // Few-shot 예제 검색
            Map<String, Object> fewShotResult = vectorRequest.getFewShots(userQuestion, "shots_api_selector", 5, null);
            
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
                        qnaService.recordFewshot(qnaId, input, input, output, i + 1);
                    }
                }
            }
            
            // 프롬프트 구성
            PromptTemplate finalTemplate = PromptTemplate.from("")
                .withSystemPrompt(systemPrompt)
                .withFewShots(fewShots)
                .withHistory(funkHistory)
                .withUserMessage(userQuestion);
            
            return new PromptWithRetrieveTime(finalTemplate, retrieveTime);
            
        } catch (Exception e) {
            log.error("Funk 프롬프트 생성 중 오류 발생: {}", e.getMessage(), e);
            
            // 오류 발생 시 기본 프롬프트 반환
            PromptTemplate template = PromptTemplate.fromFile("funk");
            String systemPrompt = template.replace("{today}", LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd")));
            
            PromptTemplate finalTemplate = PromptTemplate.from("")
                .withSystemPrompt(systemPrompt)
                .withHistory(funkHistory)
                .withUserMessage(userQuestion);
            
            return new PromptWithRetrieveTime(finalTemplate, BigDecimal.ZERO);
        }
    }

    /**
     * Params 노드용 history 조회 및 변환
     */
    public List<Map<String, Object>> getParamsHistory(String chainId) {
        List<String> requiredFields = Arrays.asList("user_question", "date_info");
        Map<String, List<Map<String, Object>>> historyDict = historyService.getHistory(chainId, requiredFields, "params", 5);
        return convertToChatHistory(historyDict, requiredFields, "user_question", "date_info");
    }

    /**
     * Params 프롬프트 생성 (few-shot 포함)
     */
    public PromptWithRetrieveTime buildParamsPromptWithFewShots(String userQuestion, List<Map<String, Object>> paramsHistory, String qnaId, String todayFormatted, String jsonFormat) {
        try {
            // Few-shot 예제 검색
            Map<String, Object> fewShotResult = vectorRequest.getFewShots(userQuestion, "shots_params_creator", 5, null);
            
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
                        
                        qnaService.recordFewshot(qnaId, input, humanWithDate, formattedOutput, i + 1);
                    }
                }
            }
            
            // 프롬프트 구성
            PromptTemplate finalTemplate = PromptTemplate.from("")
                .withSystemPrompt(systemPrompt)
                .withFewShots(fewShots)
                .withHistory(paramsHistory)
                .withUserMessage(userQuestion);
            
            return new PromptWithRetrieveTime(finalTemplate, retrieveTime);
            
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
            
            return new PromptWithRetrieveTime(finalTemplate, BigDecimal.ZERO);
        }
    }
}