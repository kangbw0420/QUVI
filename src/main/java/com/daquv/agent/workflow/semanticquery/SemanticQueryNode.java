package com.daquv.agent.workflow.semanticquery;

import com.daquv.agent.quvi.llmadmin.GenerationService;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.LlmOutputHandler;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.util.WebSocketUtils;
import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import com.daquv.agent.workflow.util.LLMRequest;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Component
public class SemanticQueryNode implements WorkflowNode {

    /**
     * SemanticQuery 노드 - 자연어 질문의 의미적 분석 및 쿼리 전략 결정
     *
     * 주요 기능:
     * 1. 질문 유형 분석 (일상대화, API호출, SQL쿼리, 복합질문 등)
     * 2. 의도 추출 (정보조회, 계산, 비교, 예측 등)
     * 3. 엔티티 추출 (날짜, 금액, 계좌, 상품명 등)
     * 4. 검색 전략 결정 (정확검색, 유사검색, 시계열검색 등)
     * 5. 쿼리 복잡도 평가 (단순, 중간, 복잡)
     */

    @Value("${api.vector-store-domain}")
    private String vectorStoreDomain;

    @Autowired
    private RestTemplate restTemplate;

    @Autowired
    private LLMRequest llmService;

    @Autowired
    private SemanticQueryPromptBuilder promptBuilder;

    @Autowired
    private GenerationService generationService;

    @Autowired
    private WebSocketUtils webSocketUtils;

    @Autowired
    private RequestProfiler requestProfiler;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public String getId() {
        return "semantic_query";
    }

    public void execute(WorkflowState state) {
        String userQuestion = state.getUserQuestion();
        String workflowId = state.getWorkflowId();

        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("사용자 질문이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다."));
            return;
        }

        // SQL 워크플로우가 아니면 건너뛰기
        if (!"SQL".equals(state.getSelectedWorkflow()) && !state.getIsApi() == Boolean.FALSE) {
            log.info("SQL 워크플로우가 아니므로 SemanticQuery 건너뜀");
            return;
        }

        log.info("=== SemanticQuery 노드 실행 시작 (SQL 쿼리 전략 분석) ===");
        log.info("분석할 질문: {}", userQuestion);

        try {
            // WebSocket 시작 메시지
            webSocketUtils.sendNodeStart(state.getWebSocketSession(), "semantic_query");

            // 1단계: SQL 쿼리 전략 분석
            SqlQueryStrategy queryStrategy = analyzeSqlQueryStrategy(userQuestion, workflowId, state);

            if (queryStrategy == null) {
                log.error("SQL 쿼리 전략 분석에 실패했습니다.");
                state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("SEMANTIC_ERROR", "쿼리 전략 분석에 실패했습니다."));
                return;
            }

            // 2단계: 분석 결과를 State에 반영
            applyQueryStrategyToState(queryStrategy, state);

            // 3단계: 쿼리 최적화 힌트 적용
            applyOptimizationHints(queryStrategy, state);

            log.info("=== SemanticQuery 노드 실행 완료 ===");
            log.info("쿼리 전략 - 유형: {}, 복잡도: {}, 테이블: {}",
                    queryStrategy.getQueryType(),
                    queryStrategy.getComplexity(),
                    queryStrategy.getTargetTables());

            // WebSocket 완료 메시지
            Map<String, Object> data = new HashMap<>();
            data.put("query_type", queryStrategy.getQueryType());
            data.put("complexity", queryStrategy.getComplexity());
            data.put("target_tables", queryStrategy.getTargetTables());
            data.put("optimization_hints", queryStrategy.getOptimizationHints());
            webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "semantic_query", data);

        } catch (Exception e) {
            log.error("SemanticQuery 노드 실행 중 예외 발생: {}", e.getMessage(), e);
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("SEMANTIC_ERROR", "SQL 쿼리 전략 분석 중 오류가 발생했습니다."));
        }
    }

    /**
     * 1단계: SQL 쿼리 전략 분석 수행
     */
    private SqlQueryStrategy analyzeSqlQueryStrategy(String userQuestion, String workflowId, WorkflowState state) {
        try {
            log.info("1단계: SQL 쿼리 전략 분석 시작");

            // QnA ID 생성
            String qnaId = generationService.createQnaId(state.getNodeId());

            // History 조회
            List<Map<String, Object>> semanticHistory = promptBuilder.getSemanticHistory(workflowId);

            // SQL 전략 분석 프롬프트 생성
            PromptTemplate promptTemplate = promptBuilder.buildSqlStrategyAnalysisPrompt(userQuestion, semanticHistory);
            String prompt = promptTemplate.build();

            log.info("SQL 전략 분석 프롬프트 생성 완료");

            // LLM 호출하여 전략 분석
            long startTime = System.currentTimeMillis();
            String llmResponse = llmService.callQwenLlm(prompt, qnaId, workflowId);
            long endTime = System.currentTimeMillis();

            // 프로파일링 기록
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordLlmCall(workflowId, elapsedTime, "semantic_sql_analysis");

            String rawOutput = LlmOutputHandler.extractAnswer(llmResponse);
            if (rawOutput == null) {
                // 짧은 응답도 허용
                rawOutput = LlmOutputHandler.handleAiColon(llmResponse);
            }

            // JSON 파싱하여 전략 분석 결과 추출
            Map<String, Object> analysisData = parseJsonOutput(rawOutput);
            SqlQueryStrategy result = mapToQueryStrategy(analysisData);

            // 벡터 검색으로 유사 쿼리 패턴 보완
            enhanceWithSimilarQueries(userQuestion, result, workflowId);

            log.info("SQL 전략 분석 완료: {}", result);
            return result;

        } catch (Exception e) {
            log.error("SQL 전략 분석 중 오류 발생: {}", e.getMessage(), e);
            return null;
        }
    }

    /**
     * 2단계: 쿼리 전략을 WorkflowState에 반영
     */
    private void applyQueryStrategyToState(SqlQueryStrategy strategy, WorkflowState state) {
        log.info("2단계: 쿼리 전략을 State에 반영");

        // 복잡도에 따른 안전 카운트 조정
        switch (strategy.getComplexity().toLowerCase()) {
            case "high":
                state.setSafeCount(0); // 복잡한 쿼리는 더 신중하게
                break;
            case "medium":
                state.setSafeCount(1);
                break;
            case "low":
                state.setSafeCount(2); // 단순한 쿼리는 빠르게
                break;
        }

        // 날짜 범위가 있으면 설정
        if (strategy.getDateRange() != null) {
            state.setStartDate(strategy.getDateRange().get("start"));
            state.setEndDate(strategy.getDateRange().get("end"));
        }

        // 페이지네이션 필요성
        if ("aggregation".equals(strategy.getQueryType()) || "summary".equals(strategy.getQueryType())) {
            state.setHasNext(false); // 집계 결과는 보통 적음
        } else if ("detail".equals(strategy.getQueryType()) || "list".equals(strategy.getQueryType())) {
            state.setHasNext(true); // 상세 조회는 많을 수 있음
        }

        log.info("쿼리 전략 State 반영 완료 - 복잡도: {}, 페이지네이션: {}",
                strategy.getComplexity(), state.getHasNext());
    }

    /**
     * 3단계: 쿼리 최적화 힌트 적용
     */
    private void applyOptimizationHints(SqlQueryStrategy strategy, WorkflowState state) {
        log.info("3단계: 쿼리 최적화 힌트 적용");

        List<String> hints = strategy.getOptimizationHints();
        if (hints != null && !hints.isEmpty()) {
            for (String hint : hints) {
                switch (hint.toLowerCase()) {
                    case "use_index":
                        log.info("인덱스 사용 힌트 적용");
                        break;
                    case "limit_early":
                        log.info("조기 LIMIT 적용 힌트");
                        break;
                    case "avoid_subquery":
                        log.info("서브쿼리 회피 힌트 적용");
                        break;
                    case "use_partition":
                        log.info("파티션 활용 힌트 적용");
                        break;
                }
            }
        }

        log.info("쿼리 최적화 힌트 적용 완료");
    }

    /**
     * 벡터 검색으로 유사 쿼리 패턴 보완
     */
    private void enhanceWithSimilarQueries(String userQuestion, SqlQueryStrategy strategy, String workflowId) {
        try {
            log.info("벡터 검색으로 유사 쿼리 패턴 보완 시작");

            long startTime = System.currentTimeMillis();

            // 유사 SQL 패턴 검색
            String similarQueriesUrl = vectorStoreDomain + "/similar_sql_patterns/" + sanitizeQuery(userQuestion);
            Map<String, Object> similarResponse = restTemplate.getForObject(similarQueriesUrl, Map.class);

            if (similarResponse != null && similarResponse.containsKey("similar_patterns")) {
                List<String> patterns = (List<String>) similarResponse.get("similar_patterns");
                strategy.setSimilarPatterns(patterns);
                log.info("유사 SQL 패턴 발견: {}", patterns);
            }

            long endTime = System.currentTimeMillis();
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordVectorDbCall(workflowId, elapsedTime, "sql_pattern_enhancement");

        } catch (Exception e) {
            log.warn("벡터 검색 보완 중 오류 (무시하고 계속): {}", e.getMessage());
        }
    }

    /**
     * JSON 출력 파싱
     */
    private Map<String, Object> parseJsonOutput(String rawOutput) throws Exception {
        try {
            return objectMapper.readValue(rawOutput, new TypeReference<Map<String, Object>>() {});
        } catch (Exception jsonError) {
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
     * 분석 데이터를 쿼리 전략 객체로 변환
     */
    private SqlQueryStrategy mapToQueryStrategy(Map<String, Object> data) {
        SqlQueryStrategy strategy = new SqlQueryStrategy();

        strategy.setQueryType((String) data.getOrDefault("query_type", "select"));
        strategy.setComplexity((String) data.getOrDefault("complexity", "medium"));
        strategy.setConfidence((Double) data.getOrDefault("confidence", 0.5));

        List<String> targetTables = (List<String>) data.getOrDefault("target_tables", new ArrayList<>());
        strategy.setTargetTables(targetTables);

        List<String> optimizationHints = (List<String>) data.getOrDefault("optimization_hints", new ArrayList<>());
        strategy.setOptimizationHints(optimizationHints);

        Map<String, String> dateRange = (Map<String, String>) data.get("date_range");
        strategy.setDateRange(dateRange);

        return strategy;
    }

    /**
     * URL 안전 문자열 변환
     */
    private String sanitizeQuery(String userQuestion) {
        return userQuestion.replaceAll("[\\\\/\"'&?#]", "-");
    }

    /**
     * SQL 쿼리 전략을 담는 클래스
     */
    public static class SqlQueryStrategy {
        private String queryType;           // select, aggregation, join, subquery, update, etc.
        private String complexity;          // low, medium, high
        private Double confidence;          // 0.0 ~ 1.0
        private List<String> targetTables = new ArrayList<>();        // 대상 테이블들
        private List<String> optimizationHints = new ArrayList<>();  // 최적화 힌트들
        private Map<String, String> dateRange;                       // 날짜 범위
        private List<String> similarPatterns = new ArrayList<>();    // 유사 패턴들

        // Getters and Setters
        public String getQueryType() { return queryType; }
        public void setQueryType(String queryType) { this.queryType = queryType; }

        public String getComplexity() { return complexity; }
        public void setComplexity(String complexity) { this.complexity = complexity; }

        public Double getConfidence() { return confidence; }
        public void setConfidence(Double confidence) { this.confidence = confidence; }

        public List<String> getTargetTables() { return targetTables; }
        public void setTargetTables(List<String> targetTables) { this.targetTables = targetTables; }

        public List<String> getOptimizationHints() { return optimizationHints; }
        public void setOptimizationHints(List<String> optimizationHints) { this.optimizationHints = optimizationHints; }

        public Map<String, String> getDateRange() { return dateRange; }
        public void setDateRange(Map<String, String> dateRange) { this.dateRange = dateRange; }

        public List<String> getSimilarPatterns() { return similarPatterns; }
        public void setSimilarPatterns(List<String> similarPatterns) { this.similarPatterns = similarPatterns; }

        @Override
        public String toString() {
            return String.format("SqlQueryStrategy{type='%s', complexity='%s', tables=%s, confidence=%.2f}",
                    queryType, complexity, targetTables, confidence);
        }
    }
}