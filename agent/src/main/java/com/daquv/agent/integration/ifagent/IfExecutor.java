package com.daquv.agent.integration.ifagent;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
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

            log.info("외부 서버로 SQL 쿼리 전송: {}{}", IFSERVER, url);

            // WebClient로 API 호출
            String responseBody = webClient.post()
                    .uri(IFSERVER + url)
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
}