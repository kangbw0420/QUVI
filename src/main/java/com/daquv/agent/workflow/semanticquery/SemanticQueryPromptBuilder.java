package com.daquv.agent.workflow.semanticquery;

import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.*;

@Component
public class SemanticQueryPromptBuilder {

    @Autowired
    private PromptBuilder promptBuilder;

    public List<Map<String, Object>> getSemanticHistory(String workflowId) {
        return promptBuilder.getHistory(workflowId,
                Arrays.asList("user_question", "question_type", "intent", "complexity", "search_strategy"),
                "semantic_query", 3);
    }

    public PromptTemplate buildSqlStrategyAnalysisPrompt(String userQuestion, List<Map<String, Object>> history) {
        String systemPrompt = "당신은 SQL 쿼리 생성을 위한 전략을 분석하는 전문가입니다.\n\n" +
                "사용자의 질문을 분석하여 최적의 SQL 쿼리 전략을 JSON 형태로 제안해주세요:\n\n" +
                "1. query_type: 쿼리 유형\n" +
                "   - select: 단순 조회\n" +
                "   - aggregation: 집계/요약\n" +
                "   - join: 테이블 조인\n" +
                "   - subquery: 서브쿼리 필요\n" +
                "   - time_series: 시계열 분석\n" +
                "   - comparison: 비교 분석\n\n" +
                "2. complexity: 쿼리 복잡도\n" +
                "   - low: 단순한 SELECT\n" +
                "   - medium: 조인이나 GROUP BY 포함\n" +
                "   - high: 복잡한 서브쿼리나 윈도우 함수\n\n" +
                "3. target_tables: 예상 대상 테이블들\n" +
                "   - [\"amt\", \"trsc\", \"stock\"] 중에서 선택\n\n" +
                "4. optimization_hints: 최적화 힌트들\n" +
                "   - use_index: 인덱스 활용\n" +
                "   - limit_early: 조기 LIMIT 적용\n" +
                "   - avoid_subquery: 서브쿼리 회피\n" +
                "   - use_partition: 파티션 활용\n\n" +
                "5. date_range: 날짜 범위 (있는 경우)\n" +
                "   - {\"start\": \"YYYYMMDD\", \"end\": \"YYYYMMDD\"}\n\n" +
                "6. confidence: 분석 신뢰도 (0.0 ~ 1.0)\n\n" +
                "응답은 반드시 유효한 JSON 형태로만 제공하세요.";

        List<Map<String, Object>> fewShots = new ArrayList<>();

        Map<String, Object> shot1 = new HashMap<>();
        shot1.put("input", "우리 회사 계좌 잔액 조회해줘");
        shot1.put("output", "{\n" +
                "  \"query_type\": \"select\",\n" +
                "  \"complexity\": \"low\",\n" +
                "  \"target_tables\": [\"amt\"],\n" +
                "  \"optimization_hints\": [\"use_index\"],\n" +
                "  \"confidence\": 0.9\n" +
                "}");
        fewShots.add(shot1);

        Map<String, Object> shot2 = new HashMap<>();
        shot2.put("input", "지난 3개월 거래 총액을 월별로 집계해줘");
        shot2.put("output", "{\n" +
                "  \"query_type\": \"aggregation\",\n" +
                "  \"complexity\": \"medium\",\n" +
                "  \"target_tables\": [\"trsc\"],\n" +
                "  \"optimization_hints\": [\"use_index\", \"use_partition\"],\n" +
                "  \"date_range\": {\"start\": \"20240401\", \"end\": \"20240723\"},\n" +
                "  \"confidence\": 0.85\n" +
                "}");
        fewShots.add(shot2);

        Map<String, Object> shot3 = new HashMap<>();
        shot3.put("input", "작년 대비 올해 예금과 주식 잔액 증감률 비교 분석");
        shot3.put("output", "{\n" +
                "  \"query_type\": \"comparison\",\n" +
                "  \"complexity\": \"high\",\n" +
                "  \"target_tables\": [\"amt\", \"stock\"],\n" +
                "  \"optimization_hints\": [\"use_index\", \"avoid_subquery\"],\n" +
                "  \"date_range\": {\"start\": \"20230101\", \"end\": \"20240723\"},\n" +
                "  \"confidence\": 0.75\n" +
                "}");
        fewShots.add(shot3);

        // History를 기존 형식으로 변환
        List<Map<String, Object>> processedHistory = new ArrayList<>();
        if (history != null && !history.isEmpty()) {
            for (Map<String, Object> entry : history) {
                String question = (String) entry.get("user_question");
                String queryType = (String) entry.get("query_type");
                String complexity = (String) entry.get("complexity");

                if (question != null && queryType != null) {
                    Map<String, Object> historyEntry = new HashMap<>();
                    historyEntry.put("user_question", String.format("Q: %s -> Type: %s, Complexity: %s", question, queryType, complexity));
                    historyEntry.put("final_answer", "이전 쿼리 전략 맥락입니다.");
                    processedHistory.add(historyEntry);
                }
            }
        }

        // 최종 사용자 질문
        String finalUserMessage = "다음 질문에 대한 SQL 쿼리 전략을 분석해주세요: " + userQuestion;

        // 기존 PromptTemplate 체이닝 방식 사용
        return PromptTemplate.from("")
                .withSystemPrompt(systemPrompt)
                .withFewShotsWithoutDateModification(fewShots)
                .withHistory(processedHistory)
                .withUserMessage(finalUserMessage);
    }
}
