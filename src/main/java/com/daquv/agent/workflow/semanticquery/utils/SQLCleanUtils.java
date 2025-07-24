package com.daquv.agent.workflow.semanticquery.utils;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Component
public class SQLCleanUtils {
    // /* ... */ 블록 주석 제거용 패턴
    private static final Pattern BLOCK_COMMENT_PATTERN = Pattern.compile(
            "/\\*.*?\\*/",
            Pattern.DOTALL
    );

    // 공백 압축용 패턴
    private static final Pattern WHITESPACE_PATTERN = Pattern.compile("\\s+");

    // DATE_TRUNC with TO_DATE 패턴들
    private static final Pattern TRSC_DT_PATTERN = Pattern.compile(
            "DATE_TRUNC\\('day',\\s*TO_DATE\\(\\s*CAST\\(\\s*trsc_dt\\s+AS\\s+TEXT\\s*\\)\\s*,\\s*'YYYY-MM-DD'\\s*\\)\\)",
            Pattern.CASE_INSENSITIVE
    );

    private static final Pattern DUE_DT_PATTERN = Pattern.compile(
            "DATE_TRUNC\\('day',\\s*(?!TO_DATE\\()\\s*due_dt\\s*\\)",
            Pattern.CASE_INSENSITIVE
    );

    private static final Pattern OPEN_DT_PATTERN = Pattern.compile(
            "DATE_TRUNC\\('day',\\s*(?!TO_DATE\\()\\s*open_dt\\s*\\)",
            Pattern.CASE_INSENSITIVE
    );

    private static final Pattern MISMATCHED_QUOTES_PATTERN = Pattern.compile("(= )'([^'\\n]*?)\"");


    public String extractCleanSql(String sqlWithComments) {
        if (sqlWithComments == null || sqlWithComments.trim().isEmpty()) {
            return "";
        }

        // /* ... */ 블록 주석 제거
        String sqlNoBlockComments = BLOCK_COMMENT_PATTERN.matcher(sqlWithComments)
                .replaceAll("");

        // -- 한 줄 주석 제거 (각 줄의 -- 이후 제거)
        StringBuilder sqlNoLineComments = new StringBuilder();
        String[] lines = sqlNoBlockComments.split("\n");

        for (String line : lines) {
            int commentIndex = line.indexOf("--");
            if (commentIndex != -1) {
                sqlNoLineComments.append(line.substring(0, commentIndex));
            } else {
                sqlNoLineComments.append(line);
            }
            sqlNoLineComments.append("\n");
        }

        // 공백 압축
        String cleanSql = WHITESPACE_PATTERN.matcher(sqlNoLineComments.toString())
                .replaceAll(" ");

        return cleanSql.trim();
    }

    /**
     * SQL 쿼리를 수정하여 날짜 포맷을 변경
     */
    public String modifyQuery(String rawSql) {
        if (rawSql == null || rawSql.trim().isEmpty()) {
            return rawSql;
        }

        String sql = rawSql;

        // trsc_dt의 DATE_TRUNC 처리
        sql = TRSC_DT_PATTERN.matcher(sql).replaceAll(
                "DATE_TRUNC('day', TO_DATE(CAST(trsc_dt AS TEXT), 'YYYYMMDD'))"
        );

        // 안전한 DATE_TRUNC 처리: TO_DATE가 없을 경우에만 due_dt 변환
        sql = DUE_DT_PATTERN.matcher(sql).replaceAll(
                "DATE_TRUNC('day', TO_DATE(due_dt, 'YYYYMMDD'))"
        );

        // open_dt도 동일하게 처리
        sql = OPEN_DT_PATTERN.matcher(sql).replaceAll(
                "DATE_TRUNC('day', TO_DATE(open_dt, 'YYYYMMDD'))"
        );

        return sql;
    }

    /**
     * 문자열 리터럴 중 '로 시작해서 "로 끝나는 경우만 수정.
     * 단, '총_잔고' AS "은행명" 같은 구문은 유지.
     */
    public static String fixMismatchedQuotes(String sql) {
        // 문자열 리터럴만 잡아냄: = '..."
        Matcher matcher = MISMATCHED_QUOTES_PATTERN.matcher(sql);
        StringBuffer result = new StringBuffer();

        while (matcher.find()) {
            String prefix = matcher.group(1);
            String content = matcher.group(2);
            matcher.appendReplacement(result, prefix + "'" + content + "'");
        }

        matcher.appendTail(result);
        return result.toString();
    }
}
