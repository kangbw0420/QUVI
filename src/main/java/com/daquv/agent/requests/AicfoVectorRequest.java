package com.daquv.agent.requests;

import com.daquv.agent.quvi.util.RequestProfiler;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Component
public class AicfoVectorRequest {

    private static final Logger log = LoggerFactory.getLogger(AicfoVectorRequest.class);

    @Autowired
    private RestTemplate restTemplate;

    @Autowired
    private RequestProfiler profiler;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${api.vector-store-domain}")
    private String VECTOR_STORE_BASE_URL;

    /**
     * 주어진 원본 노트에 대해 유사한 노트들을 벡터 API를 사용하여 검색합니다.
     *
     * @param originalNote 원본 노트
     * @param availableNotes 검색 대상 노트 리스트
     * @param topK 검색할 상위 결과 수
     * @param threshold 유사도 임계값
     * @param workflowId 프로파일링용 workflowId
     * @param nodeId 호출한 노드 ID
     * @return 유사한 노트 리스트
     */
    public List<String> getSimilarNotes(String originalNote, List<String> availableNotes, int topK, double threshold, String workflowId, String nodeId) {
        long startTime = System.currentTimeMillis();

        try {
            log.info("[aicfo_vector] getSimilarNotes 시작 - 원본노트: {}, 대상노트수: {}, nodeId: {}", originalNote, availableNotes.size(), nodeId);

            if (availableNotes == null || availableNotes.isEmpty()) {
                log.warn("[aicfo_vector] 검색 대상 노트가 없습니다 - nodeId: {}", nodeId);
                return new ArrayList<>();
            }

            List<String> similarNotes = new ArrayList<>();

            // 요청 데이터 구성
            Map<String, Object> requestData = new HashMap<>();
            List<Map<String, Object>> pickItems = new ArrayList<>();

            Map<String, Object> pickItem = new HashMap<>();
            pickItem.put("target", originalNote);
            pickItem.put("candidates", availableNotes);

            pickItems.add(pickItem);
            requestData.put("pickItems", pickItems);
            requestData.put("top_k", topK);

            // HTTP 헤더 설정
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            // HTTP 요청 생성
            HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestData, headers);

            log.info("[aicfo_vector] 노트 유사도 요청 페이로드 - nodeId: {}", nodeId);

            // API 호출
            ResponseEntity<String> response = restTemplate.postForEntity(
                    VECTOR_STORE_BASE_URL + "/pick", request, String.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                String responseBody = response.getBody();
                log.info("[aicfo_vector] 노트 유사도 검색 완료 - nodeId: {}", nodeId);

                // 응답 파싱
                JsonNode data = objectMapper.readTree(responseBody);

                if (data.has("results")) {
                    JsonNode results = data.get("results");

                    for (JsonNode resultItem : results) {
                        if (resultItem.has("target") &&
                                originalNote.equals(resultItem.get("target").asText()) &&
                                resultItem.has("candidates")) {

                            JsonNode candidates = resultItem.get("candidates");

                            for (JsonNode candidateObj : candidates) {
                                if (candidateObj.has("candidate") && candidateObj.has("score")) {
                                    String candidate = candidateObj.get("candidate").asText();
                                    double score = candidateObj.get("score").asDouble();

                                    if (score >= threshold && !similarNotes.contains(candidate)) {
                                        similarNotes.add(candidate);
                                        log.info("[aicfo_vector] 유사한 노트 발견 - nodeId: {}, candidate: '{}', 점수: {}", nodeId, candidate, score);
                                    }
                                }
                            }
                        }
                    }
                }

                log.info("[aicfo_vector] getSimilarNotes 완료 - nodeId: {}, 임계값 {} 이상의 유사노트수: {}",
                        nodeId, threshold, similarNotes.size());
                return similarNotes;

            } else {
                log.error("[aicfo_vector] 노트 유사도 검색 실패 - 상태 코드: {}, nodeId: {}", response.getStatusCode(), nodeId);
                return new ArrayList<>();
            }

        } catch (Exception e) {
            log.error("[aicfo_vector] getSimilarNotes 처리 중 오류 - nodeId: {}, 오류: {}", nodeId, e.getMessage(), e);
            return new ArrayList<>();
        } finally {
            // 프로파일링 기록
            if (workflowId != null) {
                double elapsedTime = (System.currentTimeMillis() - startTime) / 1000.0;
                profiler.recordVectorDbCall(workflowId, elapsedTime, nodeId != null ? nodeId : "aicfo_vector");
            }
        }
    }

    /**
     * 기존 호환성을 위한 오버로드 메서드 - 스택 트레이스에서 노드 ID 자동 결정
     */
    public List<String> getSimilarNotes(String originalNote, List<String> availableNotes, int topK, double threshold) {
        String nodeId = determineNodeIdFromStackTrace();
        return getSimilarNotes(originalNote, availableNotes, topK, threshold, null, nodeId);
    }

    /**
     * 스택 트레이스에서 워크플로우 노드 ID 결정
     */
    private String determineNodeIdFromStackTrace() {
        StackTraceElement[] stackTrace = Thread.currentThread().getStackTrace();

        for (StackTraceElement element : stackTrace) {
            String className = element.getClassName();
            String methodName = element.getMethodName();

            // 워크플로우 노드들 우선 체크
            if (className.contains("CheckpointNode")) return "checkpoint";
            if (className.contains("CommanderNode")) return "commander";
            if (className.contains("Nl2sqlNode")) return "nl2sql";
            if (className.contains("QueryExecutorNode")) return "executor";
            if (className.contains("SafeguardNode")) return "safeguard";
            if (className.contains("RespondentNode")) return "respondent";
            if (className.contains("NodataNode")) return "nodata";
            if (className.contains("KilljoyNode")) return "killjoy";
            if (className.contains("NextPageNode")) return "next_page";

            // 새로 추가된 노드들
            if (className.contains("DaterNode")) return "dater";
            if (className.contains("FunkNode")) return "funk";
            if (className.contains("IsApiNode")) return "isapi";
            if (className.contains("OpendueNode")) return "opendue";
            if (className.contains("ParamsNode")) return "params";
            if (className.contains("YqmdNode")) return "yqmd";

            // QueryUtils 특별 처리
            if (className.contains("QueryUtils")) {
                if (methodName.contains("everNote")) return "query_utils";
                return "query_utils";
            }

            // PromptBuilder 메서드별 분류
            if (className.contains("PromptBuilder")) {
                if (methodName.contains("Commander")) return "commander";
                if (methodName.contains("NL2SQL")) return "nl2sql";
                if (methodName.contains("Respondent")) return "respondent";
                if (methodName.contains("Nodata")) return "nodata";
                if (methodName.contains("Killjoy")) return "killjoy";
                if (methodName.contains("Dater")) return "dater";
                if (methodName.contains("Funk")) return "funk";
                if (methodName.contains("Params")) return "params";
                return "prompt_builder";
            }

            // Controller
            if (className.contains("QuviController") || className.contains("QuviWebSocketHandler")) {
                if (methodName.contains("getRecommend")) return "controller";
                return "controller";
            }
        }

        return "aicfo_vector_request";
    }
}