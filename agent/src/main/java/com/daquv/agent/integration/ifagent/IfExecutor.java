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
        List<Map<String, Object>> results = new ArrayList<Map<String, Object>>();

        if (responseBody == null || responseBody.trim().isEmpty()) {
            return results;
        }

        BufferedReader reader = null;
        try {
            reader = new BufferedReader(new StringReader(responseBody));
            String line;
            boolean isFirstLine = true;

            while ((line = reader.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty()) {
                    continue; // 빈 줄은 건너뛰기
                }

                try {
                    JsonNode jsonNode = objectMapper.readTree(line);
                    @SuppressWarnings("unchecked")
                    Map<String, Object> result = objectMapper.convertValue(jsonNode, Map.class);

                    // 첫 번째 항목이 메타데이터인 경우 로깅만 하고 건너뛰기
                    if (isFirstLine && result.containsKey("success") && result.containsKey("result_cd")) {
                        log.info("쿼리 메타데이터: {}", result);
                        isFirstLine = false;
                    } else {
                        results.add(result);
                        isFirstLine = false;
                    }
                } catch (Exception e) {
                    log.error("라인 파싱 실패: {}, 오류: {}", line, e.getMessage());
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
        if (mapList.isEmpty()) {
            RootAllocator allocator = new RootAllocator();
            return new ArrowData(allocator);
        }

        RootAllocator allocator = new RootAllocator();
        ArrowData df = new ArrowData(allocator);

        try {
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
    private static void loadFromMapList(ArrowData arrowData, List<Map<String, Object>> mapList) {
        if (mapList.isEmpty()) {
            return;
        }

        // 첫 번째 맵에서 컬럼 정보 추출
        Map<String, Object> firstRow = mapList.get(0);
        List<String> columnNamesList = new ArrayList<>(firstRow.keySet());
        int totalRows = mapList.size();

        log.info("Map List Arrow 데이터 로드 시작: {} 컬럼, {} 행", columnNamesList.size(), totalRows);

        // 컬럼 정보 수집 및 벡터 생성
        for (String columnName : columnNamesList) {
            arrowData.columnNames.add(columnName);
            arrowData.columnIndexMap.put(columnName, arrowData.columnNames.size() - 1);

            // 타입 추론
            Types.MinorType arrowType = inferTypeFromMapList(mapList, columnName);
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

        // 데이터 로드
        for (Map<String, Object> row : mapList) {
            for (int i = 0; i < columnNamesList.size(); i++) {
                String columnName = columnNamesList.get(i);
                FieldVector vector = arrowData.getVectors().get(i);
                Object value = row.get(columnName);
                arrowData.setVectorValue(vector, arrowData.rowCount, value);
            }
            arrowData.rowCount++;
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
    private static Types.MinorType inferTypeFromMapList(List<Map<String, Object>> mapList, String columnName) {
        for (Map<String, Object> row : mapList) {
            Object value = row.get(columnName);
            if (value != null) {
                if (value instanceof Long || value instanceof Integer) {
                    return Types.MinorType.BIGINT;
                } else if (value instanceof Double || value instanceof Float) {
                    return Types.MinorType.FLOAT8;
                } else if (value instanceof Boolean) {
                    return Types.MinorType.BIT;
                } else if (value instanceof java.sql.Timestamp || value instanceof java.sql.Date) {
                    return Types.MinorType.TIMESTAMPMICRO;
                } else {
                    return Types.MinorType.VARCHAR;
                }
            }
        }
        return Types.MinorType.VARCHAR;
    }
}