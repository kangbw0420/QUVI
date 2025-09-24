package com.daquv.agent.integration.ifagent;

import com.daquv.agent.workflow.util.ArrowData;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.arrow.memory.RootAllocator;
import org.apache.arrow.vector.FieldVector;
import org.apache.arrow.vector.VarCharVector;
import org.apache.arrow.vector.types.Types;
import org.apache.arrow.vector.types.pojo.Field;
import org.springframework.beans.factory.annotation.Value;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;

import java.io.BufferedReader;
import java.io.StringReader;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

@Component
@Slf4j
public class IfExecutor {
    private final WebClient webClient;
    private final ObjectMapper objectMapper;

    @Value("${ifserver.base-url}")
    private String IFSERVER;
    public static final String FETCH_ALL = "all";
    public static final String FETCH_ONE = "one";
    public static final String FETCH_CURSOR = "cursor";

    public IfExecutor(WebClient webClient, ObjectMapper objectMapper) {
        this.webClient = webClient;
        this.objectMapper = objectMapper;
    }

    /**
     * 외부 서버에서 SQL 쿼리를 실행합니다.
     *
     * @param sql          SQL 쿼리
     * @param inttBizNo    사용자 정보의 사업자 번호
     * @param inttCntrctId 사용자 약정 번호
     * @param fetch        조회 모드. "all", "one", "cursor" 중 하나
     * @return 조회 모드에 따른 쿼리 결과
     *         fetch='all': 모든 결과 행을 리스트로 반환
     *         fetch='one': 첫 번째 결과 행만 리스트로 반환
     *         fetch='cursor': 커서 객체 직접 반환 (모든 결과)
     * @throws IllegalArgumentException fetch 파라미터가 유효하지 않은 경우
     */
    public List<Map<String, Object>> executeIf(String sql, String inttBizNo, String inttCntrctId, String fetch) {
        log.info("===========IfExecute 시작===========");
        String url = String.format("%s/agent/request/%s/%s", IFSERVER, inttBizNo, inttCntrctId);

        try {
            // ifTokenHelper 토큰 생성
            ifTokenHelper.TokenInfo tokenInfo = new ifTokenHelper.TokenInfo(inttBizNo, inttCntrctId);
            String token = ifTokenHelper.generateToken(tokenInfo);
            log.debug("ifTokenHelper 토큰 생성 완료");

            // 요청 데이터 설정
            MultiValueMap<String, String> data = new LinkedMultiValueMap<>();
            data.add("sql", sql);

            log.info("외부 서버로 SQL 쿼리 전송: {}", url);

            // WebClient로 API 호출
            String responseBody = webClient.post()
                    .uri(url)
                    .header("X-TIMEOUT", "600000")
                    .header("Authorization", token)
                    .contentType(MediaType.APPLICATION_FORM_URLENCODED)
                    .body(BodyInserters.fromFormData(data))
                    .retrieve()
                    .bodyToMono(String.class)
                    .doOnNext(response -> {
                        log.info("응답 데이터: {}", response);
                    })
                    .doOnError(error -> {
                        log.error("외부 서버 호출 중 오류 발생: {}", error.getMessage(), error);
                    })
                    .onErrorReturn("")
                    .block(); // 동기 처리

            List<Map<String, Object>> results = parseResponse(responseBody);
            log.info("외부 서버로부터 {}개의 결과를 성공적으로 받았습니다", results.size());

            return processFetchMode(results, fetch);

        } catch (Exception e) {
            log.error("토큰 생성 중 오류 발생: {}", e.getMessage(), e);
            return new ArrayList<>();
        }
    }

    /**
     * 서버 응답을 파싱하여 결과 리스트로 변환합니다.
     * 각 줄이 개별 JSON 객체인 응답을 처리합니다.
     */
    private List<Map<String, Object>> parseResponse(String responseBody) {
        List<Map<String, Object>> results = new ArrayList<>();

        if (responseBody == null || responseBody.trim().isEmpty()) {
            log.warn("응답 바디가 비어있습니다.");
            return results;
        }

        log.info("파싱할 응답 데이터: {}", responseBody);

        BufferedReader reader = null;
        try {
            reader = new BufferedReader(new StringReader(responseBody));
            String line;
            int lineNumber = 0;

            while ((line = reader.readLine()) != null) {
                lineNumber++;
                line = line.trim();
                if (line.isEmpty()) {
                    continue;
                }

                try {
                    JsonNode jsonNode = objectMapper.readTree(line);
                    @SuppressWarnings("unchecked")
                    Map<String, Object> result = objectMapper.convertValue(jsonNode, Map.class);

                    log.info("파싱된 라인 {}: {}", lineNumber, result);

                    // 메타데이터 판별 로직을 더 간단하게
                    if (lineNumber == 1 && result.containsKey("success") && result.containsKey("result_cd")) {
                        log.info("메타데이터로 판별하여 건너뜀: {}", result);
                    } else {
                        results.add(result);
                        log.info("데이터로 추가: {}", result);
                    }
                } catch (Exception e) {
                    log.error("라인 {} 파싱 실패: {}, 오류: {}", lineNumber, line, e.getMessage());
                }
            }
        } catch (Exception e) {
            log.error("응답 읽기 중 오류 발생: {}", e.getMessage());
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (Exception e) {
                    log.warn("BufferedReader 닫기 실패: {}", e.getMessage());
                }
            }
        }

        log.info("최종 파싱 결과 개수: {}", results.size());
        return results;
    }

    /**
     * fetch 모드에 따라 결과를 처리합니다.
     */
    private List<Map<String, Object>> processFetchMode(List<Map<String, Object>> results, String fetch) {
        String fetchMode = fetch.toLowerCase();

        if (FETCH_ALL.equals(fetchMode)) {
            return results; // 모든 결과 반환
        } else if (FETCH_ONE.equals(fetchMode)) {
            // 첫 번째 결과만 반환
            if (results.isEmpty()) {
                return new ArrayList<Map<String, Object>>();
            } else {
                return Arrays.asList(results.get(0));
            }
        } else if (FETCH_CURSOR.equals(fetchMode)) {
            return results; // 커서 모드 (모든 결과 반환)
        } else {
            String errMsg = String.format("유효하지 않은 fetch 모드: %s", fetch);
            log.error(errMsg);
            throw new IllegalArgumentException(
                    "fetch 파라미터는 '" + FETCH_ONE + "', '" + FETCH_ALL + "', '" + FETCH_CURSOR + "' 중 하나여야 합니다");
        }
    }

    /**
     * List<Map<String, Object>>에서 Arrow 데이터 생성
     */
    public static ArrowData fromMapList(List<Map<String, Object>> mapList) {
        RootAllocator allocator = new RootAllocator();
        ArrowData df = new ArrowData(allocator);

        try {
            if (mapList == null || mapList.isEmpty()) {
                log.warn("Map list가 비어있습니다. 빈 ArrowData를 반환합니다.");
                return df;  // 빈 ArrowData 반환
            }

            loadFromMapList(df, mapList);
            return df;
        } catch (Exception e) {
            log.error("ArrowData.fromMapList 실패: {}", e.getMessage(), e);
            df.close();
            throw e;
        }
    }

    /**
     * List<Map>에서 데이터 로드
     */
    /**
     * List<Map>에서 데이터 로드
     */
    private static void loadFromMapList(ArrowData arrowData, List<Map<String, Object>> mapList) {
        if (mapList == null || mapList.isEmpty()) {
            log.warn("mapList가 null이거나 비어있습니다. 로드를 건너뜁니다.");
            return;
        }

        // 안전한 방식으로 첫 번째 행 접근
        Map<String, Object> firstRow = null;
        try {
            firstRow = mapList.get(0);
        } catch (IndexOutOfBoundsException e) {
            log.error("mapList 크기: {}, 하지만 get(0) 접근 실패: {}", mapList.size(), e.getMessage());
            return;
        }

        if (firstRow == null || firstRow.isEmpty()) {
            log.warn("첫 번째 행이 null이거나 비어있습니다.");
            return;
        }

        List<String> columnNamesList = new ArrayList<>(firstRow.keySet());
        int totalRows = mapList.size();

        log.info("Map List Arrow 데이터 로드 시작: {} 컬럼, {} 행", columnNamesList.size(), totalRows);
        log.info("실제 mapList 첫 번째 요소: {}", firstRow);
        log.info("컬럼명 리스트: {}", columnNamesList);

        // 컬럼명이 없으면 종료
        if (columnNamesList.isEmpty()) {
            log.error("컬럼명 리스트가 비어있습니다. 데이터 로드를 중단합니다.");
            return;
        }

        // 컬럼 정보 수집 및 벡터 생성
        for (String columnName : columnNamesList) {
            arrowData.columnNames.add(columnName);
            arrowData.columnIndexMap.put(columnName, arrowData.columnNames.size() - 1);

            // 타입 추론
            Types.MinorType arrowType = inferTypeFromMapList(firstRow, columnName);
            Field field = Field.nullable(columnName, arrowType.getType());

            // 벡터 생성
            FieldVector vector = field.createVector(arrowData.getAllocator());
            vector.setInitialCapacity(totalRows);

            if (vector instanceof VarCharVector) {
                ((VarCharVector) vector).allocateNew(200 * totalRows, totalRows);
            } else {
                vector.allocateNew();
            }
            arrowData.getVectors().add(vector);
        }

        log.info("벡터 생성 완료. 벡터 개수: {}, 컬럼명 개수: {}", arrowData.getVectors().size(), columnNamesList.size());

        // 데이터 로드 - 안전한 인덱스 기반 반복
        for (int rowIndex = 0; rowIndex < mapList.size(); rowIndex++) {
            try {
                Map<String, Object> row = mapList.get(rowIndex);
                if (row == null) {
                    log.warn("행 {}가 null입니다. 건너뜁니다.", rowIndex);
                    continue;
                }

                log.info("데이터 로드 중 - 행 {}: {}", rowIndex, row);

                // 벡터 리스트 크기 검증
                if (arrowData.getVectors().size() != columnNamesList.size()) {
                    log.error("벡터 개수({})와 컬럼명 개수({})가 일치하지 않습니다.",
                            arrowData.getVectors().size(), columnNamesList.size());
                    break;
                }

                for (int i = 0; i < columnNamesList.size(); i++) {
                    String columnName = columnNamesList.get(i);

                    // 벡터 리스트 범위 검증
                    if (i >= arrowData.getVectors().size()) {
                        log.error("벡터 인덱스 {} 접근 실패. 벡터 리스트 크기: {}", i, arrowData.getVectors().size());
                        break;
                    }

                    FieldVector vector = arrowData.getVectors().get(i);
                    Object value = row.get(columnName);

                    log.info("벡터에 값 설정 - 행: {}, 컬럼: {}, 값: {}", arrowData.rowCount, columnName, value);

                    arrowData.setVectorValue(vector, arrowData.rowCount, value);
                }
                arrowData.rowCount++;

            } catch (IndexOutOfBoundsException e) {
                log.error("데이터 로드 중 인덱스 {} 접근 실패. mapList 크기: {}, 벡터 크기: {}, 컬럼명 크기: {}, 오류: {}",
                        rowIndex, mapList.size(), arrowData.getVectors().size(), columnNamesList.size(), e.getMessage());
                break;
            } catch (Exception e) {
                log.error("데이터 로드 중 행 {} 처리 실패: {}", rowIndex, e.getMessage(), e);
                break;
            }
        }

        // 모든 벡터의 value count 설정
        for (FieldVector vector : arrowData.getVectors()) {
            vector.setValueCount(arrowData.rowCount);
        }

        log.info("Map List Arrow 데이터 생성 완료: {} 컬럼, {} 행", columnNamesList.size(), arrowData.rowCount);
    }

    /**
     * Map List에서 컬럼 타입 추론
     */
    private static Types.MinorType inferTypeFromMapList(Map<String, Object> firstRow, String columnName) {
        Object value = firstRow.get(columnName);
        if (value != null) {
            log.info("타입 추론 - 컬럼: {}, 값: {}, 타입: {}", columnName, value, value.getClass().getSimpleName());

            if (value instanceof Long || value instanceof Integer) {
                return Types.MinorType.BIGINT;
            } else if (value instanceof Double || value instanceof Float) {
                return Types.MinorType.FLOAT8;
            } else if (value instanceof Boolean) {
                return Types.MinorType.BIT;
            } else if (value instanceof java.sql.Timestamp || value instanceof java.sql.Date) {
                return Types.MinorType.TIMESTAMPMICRO;
            }
        }
        return Types.MinorType.VARCHAR;
    }
}