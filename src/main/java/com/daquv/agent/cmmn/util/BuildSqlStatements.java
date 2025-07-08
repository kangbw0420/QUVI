package com.daquv.agent.cmmn.util;

import org.springframework.stereotype.Component;
import lombok.extern.slf4j.Slf4j;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Slf4j
@Component
public class BuildSqlStatements {
    public Map<String, List<String>> buildSqlStatements(
            List<Map<String, Object>> modifiedData,
            List<Map<String, Object>> deletedRows,
            List<Map<String, Object>> newRows) {

        log.info("🟡 [buildSqlStatements] 입력된 데이터 상태 확인");
        log.info("🔹 modifiedData: {}", modifiedData);
        log.info("🔹 deletedRows: {}", deletedRows);
        log.info("🔹 newRows: {}", newRows);

        List<String> updateSqls = new ArrayList<>();
        List<String> deleteSqls = new ArrayList<>();
        List<String> insertSqls = new ArrayList<>();

        try {
            // 수정 SQL 생성
            if (modifiedData != null) {
                for (Map<String, Object> item : modifiedData) {
                    Object rowIdObj = item.get("rowId");
                    Integer rowId = null;

                    if (rowIdObj == null) {
                        Object rowIndexObj = item.get("rowIndex");
                        if (rowIndexObj != null) {
                            rowId = (Integer) rowIndexObj + 1;
                        }
                    } else {
                        rowId = (Integer) rowIdObj;
                    }

                    String column = (String) item.get("column");
                    Object newValue = item.get("newValue");

                    if (column != null && column.toLowerCase().equals("id")) {
                        continue;
                    }

                    String valueStr = convertToSqlValue(newValue);
                    String updateSql = String.format(
                            "UPDATE bank_product_crm SET %s = %s WHERE id = %d;",
                            column, valueStr, rowId
                    );
                    updateSqls.add(updateSql);
                }
            }

            // 삭제 SQL → 실제로는 상태 변경 SQL로 대체
            if (deletedRows != null) {
                for (Map<String, Object> item : deletedRows) {
                    log.info("🧩 [BACKEND] 삭제 항목 수신: {}", item);

                    Integer rowId = (Integer) item.get("rowId");
                    String changeReason = (String) item.getOrDefault("change_reason", "");
                    String deleteDate = (String) item.get("delete_date");

                    if (deleteDate == null) {
                        deleteDate = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
                    }

                    log.info("✅ [BACKEND] 처리 중: rowId={}, delete_date={}, reason={}",
                            rowId, deleteDate, changeReason);

                    if (deleteDate == null || deleteDate.isEmpty()) {
                        continue;
                    }

                    String escapedReason = changeReason.replace("'", "''");

                    String updateSql = String.format(
                            "UPDATE bank_product_crm SET usage_status = '중지', " +
                                    "termination_date = '%s', change_reason = '%s' WHERE id = %d;",
                            deleteDate, escapedReason, rowId
                    );

                    deleteSqls.add(updateSql);
                }
            }

            // 추가 SQL 생성
            if (newRows != null) {
                for (Map<String, Object> row : newRows) {
                    List<String> fields = row.keySet().stream()
                            .filter(key -> !key.equals("id"))
                            .collect(ArrayList::new, ArrayList::add, ArrayList::addAll);

                    String fieldsStr = String.join(", ", fields);

                    List<String> values = new ArrayList<>();
                    for (String field : fields) {
                        Object value = row.get(field);
                        values.add(convertToSqlValue(value));
                    }

                    String valuesStr = String.join(", ", values);
                    String insertSql = String.format(
                            "INSERT INTO bank_product_crm (%s) VALUES (%s);",
                            fieldsStr, valuesStr
                    );
                    insertSqls.add(insertSql);
                }
            }

            int totalSqls = updateSqls.size() + deleteSqls.size() + insertSqls.size();
            log.info("SQL 생성 완료: {}개의 SQL 문", totalSqls);

            Map<String, List<String>> result = new HashMap<>();
            result.put("update", updateSqls);
            result.put("delete", deleteSqls);
            result.put("insert", insertSqls);

            return result;

        } catch (Exception e) {
            log.error("SQL 생성 중 오류 발생: {}", e.getMessage(), e);

            Map<String, List<String>> errorResult = new HashMap<>();
            errorResult.put("update", Arrays.asList("-- Error generating UPDATE SQL: " + e.getMessage()));
            errorResult.put("delete", new ArrayList<>());
            errorResult.put("insert", new ArrayList<>());

            return errorResult;
        }
    }

    private String convertToSqlValue(Object value) {
        if (value == null) {
            return "NULL";
        } else if (value instanceof String) {
            String stringValue = (String) value;
            String escapedValue = stringValue.replace("'", "''");
            return "'" + escapedValue + "'";
        } else {
            return value.toString();
        }
    }
}
