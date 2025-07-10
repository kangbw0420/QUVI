package com.daquv.agent.workflow.util;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Component
public class NameModifierUtils {

    @Autowired
    @Qualifier("mainJdbcTemplate")
    private JdbcTemplate mainJdbcTemplate;

    private Map<String, String> stockMappings;
    private Map<String, String> bankMappings;

    @PostConstruct
    public void init() {
        this.stockMappings = loadNameMappings("stock");
        this.bankMappings = loadNameMappings("bank");
    }

    private Map<String, String> loadNameMappings(String nameType) {
        Map<String, String> mappings = new HashMap<>();

        String columnName = nameType + "_nm";
        String tableName = nameType + "name";
        String nickColumn = nameType + "_nick_nm";

        String query = String.format(
                "SELECT %s, %s FROM %s",
                nickColumn, columnName, tableName
        );

        try {
            List<Map<String, Object>> result = mainJdbcTemplate.queryForList(query);

            for (Map<String, Object> row : result) {
                String nickName = (String) row.get(nickColumn);
                String fullName = (String) row.get(columnName);
                if (nickName != null && fullName != null) {
                    mappings.put(nickName, fullName);
                }
            }

        } catch (Exception e) {
            System.err.println("Error loading " + nameType + " mappings: " + e.getMessage());
        }

        return mappings;
    }

    private List<PatternMatch> findAllPatterns(String query, String nameType) {
        List<PatternMatch> patterns = new ArrayList<>();
        String columnName = nameType + "_nm";

        // Equal pattern: column_nm = 'value'
        String equalPattern = columnName + "\\s*=\\s*'([^']*)'";
        Pattern equalRegex = Pattern.compile(equalPattern, Pattern.CASE_INSENSITIVE);
        Matcher equalMatcher = equalRegex.matcher(query);
        while (equalMatcher.find()) {
            patterns.add(new PatternMatch(
                    equalMatcher.group(1),
                    "=",
                    equalMatcher.group(0)
            ));
        }

        // IN pattern: column_nm IN (values)
        String inPattern = columnName + "\\s+IN\\s*\\(([^)]*)\\)";
        Pattern inRegex = Pattern.compile(inPattern, Pattern.CASE_INSENSITIVE);
        Matcher inMatcher = inRegex.matcher(query);
        while (inMatcher.find()) {
            patterns.add(new PatternMatch(
                    inMatcher.group(1),
                    "IN",
                    inMatcher.group(0)
            ));
        }

        // LIKE pattern: column_nm LIKE '%value%'
        String likePattern = columnName + "\\s+LIKE\\s+'%([^%]+)%'";
        Pattern likeRegex = Pattern.compile(likePattern, Pattern.CASE_INSENSITIVE);
        Matcher likeMatcher = likeRegex.matcher(query);
        while (likeMatcher.find()) {
            patterns.add(new PatternMatch(
                    likeMatcher.group(1),
                    "LIKE",
                    likeMatcher.group(0)
            ));
        }

        return patterns;
    }

    private String modifyQuery(String query, String nameType, Map<String, String> nameMappings) {
        List<PatternMatch> patterns = findAllPatterns(query, nameType);
        String modifiedQuery = query;
        String columnName = nameType + "_nm";

        for (PatternMatch pattern : patterns) {
            String namesStr = pattern.getValue();
            String operator = pattern.getOperator();
            String fullMatch = pattern.getFullMatch();

            // 공백 제거
            String normalizedName = namesStr.replaceAll("\\s+", "");

            if ("=".equals(operator)) {
                String officialName = nameMappings.get(normalizedName);
                if (officialName != null) {
                    String newCondition = columnName + " = '" + officialName + "'";
                    modifiedQuery = modifiedQuery.replace(fullMatch, newCondition);
                }
            } else if ("IN".equals(operator)) {
                // Split the values and process each one
                String[] values = namesStr.split(",");
                List<String> newValues = new ArrayList<>();

                for (String value : values) {
                    String trimmedValue = value.trim().replaceAll("^['\"]|['\"]$", "");
                    String normalizedValue = trimmedValue.replaceAll("\\s+", "");
                    String officialName = nameMappings.get(normalizedValue);

                    if (officialName != null) {
                        newValues.add("'" + officialName + "'");
                    } else {
                        newValues.add("'" + trimmedValue + "'");
                    }
                }

                String newCondition = columnName + " IN (" + String.join(", ", newValues) + ")";
                modifiedQuery = modifiedQuery.replace(fullMatch, newCondition);

            } else if ("LIKE".equals(operator)) {
                String officialName = nameMappings.get(normalizedName);
                if (officialName != null) {
                    String newCondition = columnName + " LIKE '%" + officialName + "%'";
                    modifiedQuery = modifiedQuery.replace(fullMatch, newCondition);
                }
            }
        }

        return modifiedQuery;
    }

    public String modifyStock(String query) {
        return modifyQuery(query, "stock", stockMappings);
    }

    public String modifyBank(String query) {
        return modifyQuery(query, "bank", bankMappings);
    }

    // 내부 클래스
    private static class PatternMatch {
        private String value;
        private String operator;
        private String fullMatch;

        public PatternMatch(String value, String operator, String fullMatch) {
            this.value = value;
            this.operator = operator;
            this.fullMatch = fullMatch;
        }

        public String getValue() { return value; }
        public String getOperator() { return operator; }
        public String getFullMatch() { return fullMatch; }
    }
}