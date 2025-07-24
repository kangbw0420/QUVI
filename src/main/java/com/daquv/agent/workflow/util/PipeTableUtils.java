package com.daquv.agent.workflow.util;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class PipeTableUtils {

    /**
     * 데이터를 파이프(|) 형식의 표로 변환.
     * 10행 초과 시 상위 5개 + 하위 5개를 출력하고, 중간은 생략 메시지로 표시.
     */
    public String pipeTable(Object data) {
        try {
            List<Map<String, Object>> dataList = convertToDataList(data);
            
            // 빈 데이터 확인
            if (dataList == null || dataList.isEmpty()) {
                return "(데이터 없음)";
            }

            // 첫 번째 데이터 항목에서 키를 가져와 헤더로 사용
            Map<String, Object> firstRow = dataList.get(0);
            List<String> headers = new ArrayList<>(firstRow.keySet());
            
            // 헤더 생성
            StringBuilder table = new StringBuilder();
            table.append(String.join(" | ", headers)).append("\n");
            
            // 구분선 생성
            int totalHeaderLength = headers.stream().mapToInt(String::length).sum();
            int separatorLength = totalHeaderLength + (headers.size() - 1) * 3;
            table.append(repeatString("-", separatorLength)).append("\n");

            int totalRows = dataList.size();

            // 행 개수에 따라 출력 방식 결정
            List<Map<String, Object>> displayRows;
            if (totalRows <= 10) {
                displayRows = dataList;
            } else {
                displayRows = new ArrayList<>();
                displayRows.addAll(dataList.subList(0, 5));

                Map<String, Object> ellipsisMap = new HashMap<>();
                ellipsisMap.put("__ellipsis__", true);
                displayRows.add(ellipsisMap);

                displayRows.addAll(dataList.subList(totalRows - 5, totalRows));
            }
            // 행 출력
            for (Map<String, Object> row : displayRows) {
                if (row.containsKey("__ellipsis__")) {
                    table.append("... (중간 생략) ...\n");
                    continue;
                }
                
                List<String> rowValues = new ArrayList<>();
                for (String header : headers) {
                    Object value = row.get(header);
                    rowValues.add(value != null ? value.toString() : "");
                }
                table.append(String.join(" | ", rowValues)).append("\n");
            }

            return table.toString();

        } catch (Exception e) {
            log.error("테이블 형식 변환 오류: {}", e.getMessage(), e);
            return "(테이블 형식 변환 오류: " + e.getMessage() + ")";
        }
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> convertToDataList(Object data) {
        try {
            // 튜플 처리 - 튜플에 단일 리스트가 있는 경우 추출
            if (data instanceof List && ((List<?>) data).size() == 1) {
                Object firstElement = ((List<?>) data).get(0);
                if (firstElement instanceof List) {
                    data = firstElement;
                }
            }
            
            // 입력이 리스트가 아니면 변환 시도
            if (!(data instanceof List)) {
                if (data instanceof Iterable) {
                    List<Object> tempList = new ArrayList<>();
                    for (Object item : (Iterable<?>) data) {
                        tempList.add(item);
                    }
                    data = tempList;
                } else {
                    return null;
                }
            }
            
            List<?> rawList = (List<?>) data;
            if (rawList.isEmpty()) {
                return new ArrayList<>();
            }
            
            // 중첩 데이터 간단 확인 (data 키가 있고 그 안에 리스트가 있는 경우만 처리)
            if (rawList.get(0) instanceof Map) {
                Map<String, Object> firstItem = (Map<String, Object>) rawList.get(0);
                if (firstItem.containsKey("data") && firstItem.get("data") instanceof List) {
                    List<Map<String, Object>> flatData = new ArrayList<>();
                    for (Object item : rawList) {
                        if (item instanceof Map) {
                            Map<String, Object> mapItem = (Map<String, Object>) item;
                            if (mapItem.containsKey("data") && mapItem.get("data") instanceof List) {
                                flatData.addAll((List<Map<String, Object>>) mapItem.get("data"));
                            }
                        }
                    }
                    return flatData.isEmpty() ? (List<Map<String, Object>>) rawList : flatData;
                }
            }

            // 데이터 형식 확인
            if (!(rawList.get(0) instanceof Map)) {
                return null;
            }

            return (List<Map<String, Object>>) rawList;
            
        } catch (Exception e) {
            log.error("데이터 변환 오류: {}", e.getMessage(), e);
            return null;
        }
    }


    private String repeatString(String str, int count) {
        if (count <= 0) {
            return "";
        }
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < count; i++) {
            sb.append(str);
        }
        return sb.toString();
    }
} 