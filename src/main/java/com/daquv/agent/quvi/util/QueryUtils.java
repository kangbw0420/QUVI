package com.daquv.agent.quvi.util;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import com.daquv.agent.quvi.requests.QueryRequest;
import com.daquv.agent.quvi.requests.VectorRequest;
import com.daquv.agent.quvi.requests.ColumnRequest;

import lombok.extern.slf4j.Slf4j;

@Slf4j
@Component
public class QueryUtils {

    @Autowired
    @Qualifier("mainJdbcTemplate")
    private JdbcTemplate mainJdbcTemplate;

    @Autowired
    private QueryRequest queryRequest;
    
    @Autowired
    private VectorRequest vectorRequest;
    
    @Autowired
    private ColumnRequest columnRequest;

    /**
     * 회사명 조건이 없는 SQL 쿼리에 모든 테이블에 대해 회사명 조건 추가
     */
    public String addComCondition(String query, String companyId) {
        try {
            // UNION 처리 (재귀적으로 각 부분 처리)
            if (query.toUpperCase().contains(" UNION ")) {
                String[] parts = query.split(" UNION ");
                List<String> filteredParts = new ArrayList<>();
                for (String part : parts) {
                    filteredParts.add(addComCondition(part.trim(), companyId));
                }
                return String.join(" UNION ", filteredParts);
            }

            // 쿼리 표준화
            String normalizedQuery = normalizeQuery(query);

            // 테이블 정보 추출
            List<TableAlias> tables = extractTableAliases(normalizedQuery);

            // 회사명 조건 생성
            String companyCondition;
            if (tables.isEmpty()) {
                // 기본 테이블을 찾을 수 없는 경우, 테이블 별칭 없이 조건 추가
                companyCondition = String.format("com_nm = '%s'", companyId);
            } else {
                // 모든 테이블에 대한 회사명 조건 생성
                List<String> companyConditions = new ArrayList<>();
                for (TableAlias table : tables) {
                    companyConditions.add(String.format("%s.com_nm = '%s'", table.alias, companyId));
                }
                companyCondition = String.join(" AND ", companyConditions);
            }

            // WHERE 절 처리
            return addWhereCondition(normalizedQuery, companyCondition);

        } catch (Exception e) {
            log.error("addComCondition 처리 중 오류 발생: {}", e.getMessage());
            return query;
        }
    }

    /**
     * SQL 쿼리의 포맷을 표준화
     */
    private String normalizeQuery(String query) {
        // 여러 줄의 공백을 한 줄로
        query = query.replaceAll("\\s+", " ");
        // 괄호 주위 공백 정리
        query = query.replaceAll("\\s*\\(\\s*", " (");
        query = query.replaceAll("\\s*\\)\\s*", ") ");
        // 쉼표 뒤 공백 추가
        query = query.replaceAll(",\\s*", ", ");
        return query.trim();
    }

    /**
     * 테이블 별칭 정보를 담는 클래스
     */
    private static class TableAlias {
        String tableName;
        String alias;
        
        TableAlias(String tableName, String alias) {
            this.tableName = tableName;
            this.alias = alias;
        }
    }

    /**
     * SQL 쿼리에서 테이블 이름과 별칭을 정확하게 추출
     */
    private List<TableAlias> extractTableAliases(String query) {
        List<TableAlias> tables = new ArrayList<>();
        
        // SQL 키워드 목록 (테이블명이나 별칭으로 사용되면 안 되는 단어들)
        Set<String> sqlKeywords = new HashSet<>();
        String[] keywords = {
                "SELECT", "FROM", "WHERE", "JOIN", "INNER", "LEFT", "RIGHT", "OUTER",
                "FULL", "CROSS", "ON", "AND", "OR", "NOT", "GROUP", "ORDER", "BY",
                "HAVING", "LIMIT", "OFFSET", "UNION", "ALL", "AS", "DISTINCT", "BETWEEN"
        };
        sqlKeywords.addAll(Arrays.asList(keywords));

        // FROM 절 추출
        Pattern fromPattern = Pattern.compile("\\bFROM\\s+(\\w+)(?:\\s+(?:AS\\s+)?(\\w+))?", Pattern.CASE_INSENSITIVE);
        Matcher fromMatcher = fromPattern.matcher(query);
        if (fromMatcher.find()) {
            String tableName = fromMatcher.group(1);
            String alias = fromMatcher.group(2) != null ? fromMatcher.group(2) : tableName;
            
            // SQL 키워드가 아닌지 확인
            if (!sqlKeywords.contains(tableName.toUpperCase()) && !sqlKeywords.contains(alias.toUpperCase())) {
                tables.add(new TableAlias(tableName, alias));
            }
        }

        // JOIN 절 추출
        Pattern joinPattern = Pattern.compile(
            "\\b(?:INNER|LEFT|RIGHT|FULL|CROSS)?\\s*JOIN\\s+(\\w+)(?:\\s+(?:AS\\s+)?(\\w+))?\\s+ON\\b",
            Pattern.CASE_INSENSITIVE
        );
        Matcher joinMatcher = joinPattern.matcher(query);
        while (joinMatcher.find()) {
            String tableName = joinMatcher.group(1);
            String alias = joinMatcher.group(2) != null ? joinMatcher.group(2) : tableName;
            
            // SQL 키워드가 아닌지 확인
            if (!sqlKeywords.contains(tableName.toUpperCase()) && !sqlKeywords.contains(alias.toUpperCase())) {
                tables.add(new TableAlias(tableName, alias));
            }
        }

        return tables;
    }

    /**
     * WHERE 조건을 쿼리에 추가
     */
    private String addWhereCondition(String query, String condition) {
        // WHERE 절 찾기
        Pattern wherePattern = Pattern.compile("\\bWHERE\\b", Pattern.CASE_INSENSITIVE);
        Matcher whereMatcher = wherePattern.matcher(query);
        
        if (whereMatcher.find()) {
            // WHERE 절이 있으면 AND 조건으로 추가
            int position = whereMatcher.end();
            return query.substring(0, position) + " " + condition + " AND " + query.substring(position).trim();
        } else {
            // WHERE 절이 없으면 새로운 WHERE 절 추가
            // ORDER BY, GROUP BY, HAVING, LIMIT 등의 위치 찾기
            String[] endClauses = {"ORDER BY", "GROUP BY", "HAVING", "LIMIT"};
            List<Integer> positions = new ArrayList<>();
            
            for (String clause : endClauses) {
                Pattern clausePattern = Pattern.compile("\\b" + clause + "\\b", Pattern.CASE_INSENSITIVE);
                Matcher clauseMatcher = clausePattern.matcher(query);
                if (clauseMatcher.find()) {
                    positions.add(clauseMatcher.start());
                }
            }
            
            if (!positions.isEmpty()) {
                // 가장 앞에 있는 절의 위치에 WHERE 절 삽입
                int insertPosition = java.util.Collections.min(positions);
                return query.substring(0, insertPosition).trim() + " WHERE " + condition + " " + 
                       query.substring(insertPosition).trim();
            } else {
                // 끝에 WHERE 절 추가
                return query.trim() + " WHERE " + condition;
            }
        }
    }

    /**
     * SQL 쿼리에 ORDER BY절 추가
     */
    public String addOrderBy(String query) {
        try {
            // 간단한 구현 - 실제로는 Python API로 요청
            return queryRequest.addOrderBy(query);
        } catch (Exception e) {
            log.error("addOrderBy 처리 중 오류 발생: {}", e.getMessage());
            return query;
        }
    }

    /**
     * 결과 데이터가 있지만 모든 값이 None/null인지 확인
     * Python: is_null_only 함수와 동일
     */
    public boolean isNullOnly(List<Map<String, Object>> queryResult) {
        if (queryResult == null || queryResult.isEmpty()) {
            return true;
        }

        for (Map<String, Object> row : queryResult) {
            if (row == null) {
                continue;
            }
            
            for (Object value : row.values()) {
                if (value != null) {
                    return false;
                }
            }
        }
        
        return true;
    }

    /**
     * SQL 쿼리에서 특정 컬럼의 조건을 찾아 반환
     */
    public List<String> findColumnConditions(String query, String columnName) {
        try {
            // ColumnRequest로 요청
            return columnRequest.findColumnConditions(query, columnName);
        } catch (Exception e) {
            log.error("findColumnConditions 처리 중 오류 발생: {}", e.getMessage());
            return new ArrayList<>();
        }
    }

    /**
     * ever_note 처리 - 자바가 해야할 부분만 구현
     * 1. note1 조건 추출 (Python API)
     * 2. 모든 노트 조회 (Java 구현)
     * 3. 벡터 검색 (Java 구현)
     * 4. 쿼리 변환 (Python API)
     */
    public Map<String, Object> everNote(String query) {
        try {
            log.info("everNote 처리 시작: {}", query.substring(0, Math.min(query.length(), 100)));

            // 1. note1 조건 추출 (ColumnRequest)
            List<Map<String, Object>> noteConditions = columnRequest.findNoteConditions(query);
            if (noteConditions.isEmpty()) {
                log.info("note1 조건을 찾을 수 없습니다");
                return createEmptyEverNoteResult();
            }

            // 원본 노트 값 추출
            List<String> originalNotes = new ArrayList<>();
            for (Map<String, Object> condition : noteConditions) {
                String value = (String) condition.get("value");
                if (value != null) {
                    originalNotes.add(value);
                }
            }

            // 2. 모든 노트 조회 (Java 구현)
            List<String> availableNotes = getAllNotes(query);
            if (availableNotes.isEmpty()) {
                log.info("사용 가능한 노트가 없습니다");
                return createEverNoteResult("", originalNotes, new ArrayList<>());
            }

            // 3. 벡터 검색 (VectorRequest)
            Set<String> allSimilarNotes = new HashSet<>();
            for (String originalNote : new HashSet<>(originalNotes)) {
                List<String> similarNotes = vectorRequest.getSimilarNotes(originalNote, availableNotes, 10, 0.1);
                allSimilarNotes.addAll(similarNotes);
            }

            // 4. 쿼리 변환 (ColumnRequest)
            String modifiedQuery = columnRequest.transformQueryWithSimilarNotes(query, noteConditions, allSimilarNotes);

            log.info("everNote 처리 완료 - 유사 노트 개수: {}", allSimilarNotes.size());
            return createEverNoteResult(modifiedQuery, originalNotes, new ArrayList<>(allSimilarNotes));

        } catch (Exception e) {
            log.error("everNote 처리 중 오류 발생: {}", e.getMessage());
            return createEmptyEverNoteResult();
        }
    }

    /**
     * 쿼리에서 함수 매개변수 추출하여 모든 노트 조회
     */
    private List<String> getAllNotes(String query) {
        try {
            // aicfo_get_all_xxx 함수에서 매개변수 추출
            Pattern pattern = Pattern.compile("aicfo_get_all_\\w+\\('([^']+)', '([^']+)', '([^']+)', '([^']+)', '([^']+)'\\)", Pattern.CASE_INSENSITIVE);
            Matcher matcher = pattern.matcher(query);

            if (!matcher.find()) {
                log.warn("aicfo_get_all_xxx 함수 매개변수를 찾을 수 없습니다");
                return new ArrayList<>();
            }

            String useInttId = matcher.group(1);
            String userId = matcher.group(2);
            String company = matcher.group(3);
            String fromDate = matcher.group(4);
            String toDate = matcher.group(5);

            // aicfo_get_all_note 함수 호출
            String noteQuery = String.format("SELECT * FROM aicfo_get_all_note('%s', '%s', '%s', '%s', '%s')",
                    useInttId, userId, company, fromDate, toDate);

            List<Map<String, Object>> noteResults = mainJdbcTemplate.queryForList(noteQuery);
            List<String> availableNotes = new ArrayList<>();

            for (Map<String, Object> noteResult : noteResults) {
                String note = (String) noteResult.get("every_note");
                if (note != null && !note.trim().isEmpty()) {
                    availableNotes.add(note);
                }
            }

            log.info("사용 가능한 노트 개수: {}", availableNotes.size());
            return availableNotes;

        } catch (Exception e) {
            log.error("getAllNotes 처리 중 오류 발생: {}", e.getMessage());
            return new ArrayList<>();
        }
    }


    /**
     * everNote 결과 생성 헬퍼 메서드
     */
    private Map<String, Object> createEverNoteResult(String query, List<String> originNotes, List<String> vectorNotes) {
        Map<String, Object> result = new HashMap<>();
        result.put("query", query);
        result.put("origin_note", new ArrayList<>(new HashSet<>(originNotes)));
        result.put("vector_notes", vectorNotes);
        return result;
    }

    /**
     * 빈 everNote 결과 생성
     */
    private Map<String, Object> createEmptyEverNoteResult() {
        return createEverNoteResult("", new ArrayList<>(), new ArrayList<>());
    }
}