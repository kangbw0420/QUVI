package com.daquv.agent.quvi.util;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * LLM 출력을 파싱하고 처리하는 유틸리티 클래스
 * old_back_agent의 llm_output_handler.py를 Java로 마이그레이션
 */
public class LlmOutputHandler {
    
    private static final Logger log = LoggerFactory.getLogger(LlmOutputHandler.class);

    /**
     * AI 콜론 제거 (ai: 로 시작하는 부분 제거)
     */
    public static String handleAiColon(String output) {
        if (output == null || output.trim().isEmpty()) {
            return output;
        }
        
        // 모든 줄의 시작 부분에서 ai: 제거 (대소문자 구분 없음)
        return output.replaceAll("(?i)^ai:\\s*", "").trim();
    }

    /**
     * 따옴표 제거 (답변이 "로 감싸져 있는 경우 제거)
     */
    public static String handleQuotes(String output) {
        if (output == null || output.trim().isEmpty()) {
            return output;
        }
        
        String result = output.trim();
        
        // 앞뒤 따옴표 제거 (큰따옴표, 작은따옴표 모두 처리)
        if ((result.startsWith("\"") && result.endsWith("\"")) ||
            (result.startsWith("'") && result.endsWith("'"))) {
            result = result.substring(1, result.length() - 1);
        }
        
        return result;
    }

    /**
     * Python 코드 블록 처리
     */
    public static String handlePythonCodeBlock(String output) {
        if (output == null || output.trim().isEmpty()) {
            return output;
        }
        
        String result = output.trim();
        
        // ```python\n 제거
        if (result.startsWith("```python\n")) {
            result = result.substring(10);
        } else if (result.startsWith("```python")) {
            result = result.substring(9);
        }
        
        // 끝의 ``` 제거
        if (result.endsWith("\n```")) {
            result = result.substring(0, result.length() - 4);
        } else if (result.endsWith("```")) {
            result = result.substring(0, result.length() - 3);
        }
        
        return result;
    }

    /**
     * SQL 코드 블록 처리 (old_back_agent의 handle_sql_code_block과 동일한 로직)
     */
    public static String handleSqlCodeBlock(String output) {
        if (output == null || output.trim().isEmpty()) {
            return output;
        }
        
        // 1순위: SQL 코드블록 ```sql ... ```
        Pattern sqlBlockPattern = Pattern.compile("```sql\\s*(.*?)\\s*```", Pattern.DOTALL | Pattern.CASE_INSENSITIVE);
        Matcher sqlBlockMatcher = sqlBlockPattern.matcher(output);
        if (sqlBlockMatcher.find()) {
            return sqlBlockMatcher.group(1).trim();
        }
        
        // 2순위: WITH 쿼리 (CTE)
        Pattern withPattern = Pattern.compile("WITH.*", Pattern.DOTALL | Pattern.CASE_INSENSITIVE);
        Matcher withMatcher = withPattern.matcher(output);
        if (withMatcher.find()) {
            return withMatcher.group(0).trim();
        }
        
        // 3순위: SELECT 쿼리
        Pattern selectPattern = Pattern.compile("SELECT.*", Pattern.DOTALL | Pattern.CASE_INSENSITIVE);
        Matcher selectMatcher = selectPattern.matcher(output);
        if (selectMatcher.find()) {
            return selectMatcher.group(0).trim();
        }
        
        // 최후: 원본 텍스트 반환
        log.warn("No SQL pattern matched, using entire output as SQL query");
        return output;
    }

    /**
     * SQL 쿼리 추출 (NL2SQL, Safeguard 노드용)
     */
    public static String extractSqlQuery(String llmResponse) {
        if (llmResponse == null || llmResponse.trim().isEmpty()) {
            return null;
        }
        
        // SQL 코드 블록에서 쿼리 추출
        String sqlQuery = handleSqlCodeBlock(llmResponse);
        
        if (sqlQuery == null || sqlQuery.isEmpty()) {
            // 세미콜론이 없는 경우에도 처리
            Pattern pattern = Pattern.compile("(SELECT[\\s\\S]+?)(?:;|\\Z)", Pattern.CASE_INSENSITIVE);
            Matcher matcher = pattern.matcher(llmResponse);
            if (matcher.find()) {
                sqlQuery = matcher.group(1).trim();
            }
        }
        
        return sqlQuery;
    }

    /**
     * 테이블명 추출 (Commander 노드용)
     */
    public static String extractTableName(String llmResponse) {
        if (llmResponse == null || llmResponse.trim().isEmpty()) {
            return null;
        }
        
        // 응답에서 테이블명 추출 (공백 제거)
        String tableName = llmResponse.trim();
        
        // 유효한 테이블명인지 확인
        String[] validTables = {
            "DGC_INFO", "DGC_PURREF", "DGC_GIFT", "DGC_PAYMENT", 
            "DGC_BALANCE_GA", "DGC_BALANCE_TX", "USER_JOIN"
        };
        
        for (String validTable : validTables) {
            if (tableName.equalsIgnoreCase(validTable)) {
                return validTable;
            }
        }
        
        log.warn("유효하지 않은 테이블명: {}", tableName);
        return null;
    }

    /**
     * 일반 답변 추출 (Respondent, Killjoy, Nodata 노드용)
     */
    public static String extractAnswer(String llmResponse) {
        if (llmResponse == null || llmResponse.trim().isEmpty()) {
            return null;
        }
        
        // AI 콜론 제거
        String answer = handleAiColon(llmResponse);
        
        // 따옴표 제거
        answer = handleQuotes(answer);
        
        // 기본적인 검증
        if (answer.length() < 10) {
            log.warn("답변이 너무 짧습니다: {}", answer);
            return null;
        }
        
        return answer;
    }

    /**
     * FString 답변 추출 (Respondent 노드의 fstring용)
     */
    public static String extractFStringAnswer(String llmResponse) {
        if (llmResponse == null || llmResponse.trim().isEmpty()) {
            return null;
        }
        
        // AI 콜론 제거
        String answer = handleAiColon(llmResponse);
        
        // 따옴표 제거
        answer = handleQuotes(answer);
        
        // 기본적인 검증
        if (answer.length() < 5) {
            log.warn("FString 답변이 너무 짧습니다: {}", answer);
            return null;
        }
        
        return answer;
    }
} 