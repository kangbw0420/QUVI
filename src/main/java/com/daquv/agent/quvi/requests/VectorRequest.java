package com.daquv.agent.quvi.requests;

import com.daquv.agent.quvi.util.RequestProfiler;
import com.fasterxml.jackson.core.JsonProcessingException;
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

import javax.annotation.PostConstruct;
import java.util.*;

@Component
public class VectorRequest {
    
    private static final Logger log = LoggerFactory.getLogger(VectorRequest.class);

    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();
    @Value("${api.vector-store-domain}")
    private String VECTOR_STORE_BASE_URL;
    
    @Autowired
    private RequestProfiler profiler;
    
    @PostConstruct
    public void init() {
        log.info("[vector] VectorRequest 초기화 - profiler: {}", profiler != null ? "주입됨" : "null");
    }

    /**
     * 벡터 스토어에 쿼리를 보내 유사한 예제들을 검색합니다.
     *
     * @param queryText 검색할 쿼리 텍스트
     * @param collectionName 컬렉션 이름
     * @param topK 검색할 상위 결과 수
     * @param chainId 프로파일링용 chain_id
     * @return 검색된 문서와 메타데이터를 포함하는 결과 리스트
     */
    public List<Map<String, Object>> queryVectorStore(String queryText, String collectionName, int topK, String chainId) {
        long startTime = System.currentTimeMillis();
        
        try {
            log.info("[vector] 벡터 스토어 쿼리 시작 - 쿼리: {}, 컬렉션: {}, topK: {}", 
                    queryText, collectionName, topK);

            // 요청 데이터 구성
            Map<String, Object> requestData = new HashMap<>();
            requestData.put("collection_name", collectionName);
            requestData.put("query_text", queryText);
            requestData.put("top_k", topK);

            // HTTP 헤더 설정
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            // HTTP 요청 생성
            HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestData, headers);

            // API 호출
            ResponseEntity<String> response = restTemplate.postForEntity(
                VECTOR_STORE_BASE_URL + "/query", request, String.class);

            double retrieveTime = (System.currentTimeMillis() - startTime) / 1000.0;
            
            // 프로파일링 기록
            if (chainId != null) {
                profiler.recordVectorDbCall(chainId, retrieveTime);
                log.info("[vector] 프로파일링 기록 완료 - chainId: {}", chainId);
            } else {
                log.warn("[vector] 프로파일링 기록 실패 - chainId가 null임");
            }
            
            if (response.getStatusCode().is2xxSuccessful()) {
                String responseBody = response.getBody();
                log.info("[vector] 벡터 스토어 쿼리 완료 - 소요시간: {}s, 응답: {}", retrieveTime, responseBody);
                
                return parseVectorStoreResponse(responseBody, retrieveTime);
            } else {
                log.error("[vector] 벡터 스토어 쿼리 실패 - 상태 코드: {}", response.getStatusCode());
                return new ArrayList<>();
            }

        } catch (Exception e) {
            double elapsedTime = (System.currentTimeMillis() - startTime) / 1000.0;
            
            // 예외 발생 시에도 프로파일링 기록
            if (chainId != null) {
                profiler.recordVectorDbCall(chainId, elapsedTime);
                log.info("[vector] 예외 발생 시 프로파일링 기록 완료 - chainId: {}", chainId);
            } else {
                log.warn("[vector] 예외 발생 시 프로파일링 기록 실패 - chainId가 null임");
            }
            
            log.error("[vector] 벡터 스토어 쿼리 중 예외 발생 - 소요시간: {}s, 오류: {}", elapsedTime, e.getMessage(), e);
            return new ArrayList<>();
        }
    }

    /**
     * 벡터 스토어 응답을 파싱하여 결과 리스트로 변환합니다.
     */
    private List<Map<String, Object>> parseVectorStoreResponse(String responseBody, double retrieveTime) {
        List<Map<String, Object>> formattedResults = new ArrayList<>();
        
        try {
            JsonNode data = objectMapper.readTree(responseBody);
            
            if (data.has("results")) {
                JsonNode results = data.get("results");
                
                if (results.has("documents") && results.has("metadatas")) {
                    JsonNode documents = results.get("documents");
                    JsonNode metadatas = results.get("metadatas");
                    
                    // documents와 metadatas를 쌍으로 묶어서 결과 생성
                    for (int i = 0; i < documents.size() && i < metadatas.size(); i++) {
                        Map<String, Object> result = new HashMap<>();
                        result.put("document", documents.get(i).asText());
                        result.put("metadata", objectMapper.convertValue(metadatas.get(i), Map.class));
                        result.put("retrieve_time", retrieveTime);
                        formattedResults.add(result);
                    }
                }
            }
            
            return formattedResults;
            
        } catch (JsonProcessingException e) {
            log.error("[vector] 벡터 스토어 응답 파싱 중 오류: {}", e.getMessage(), e);
            return new ArrayList<>();
        }
    }

    /**
     * 벡터 스토어 검색 결과를 few-shot 예제 형식으로 변환합니다.
     *
     * @param results 벡터 스토어 검색 결과
     * @return few-shot 예제 리스트와 검색 처리 시간
     */
    public Map<String, Object> formatFewShots(List<Map<String, Object>> results) {
        List<Map<String, Object>> fewShots = new ArrayList<>();
        double retrieveTime = 0.0;
        
        try {
            for (Map<String, Object> result : results) {
                if (result.containsKey("document")) {
                    String document = (String) result.get("document");
                    retrieveTime = (Double) result.getOrDefault("retrieve_time", 0.0);

                    // document에서 질문 추출
                    String question = document.trim();

                    // 메타데이터에서 SQL 답변 찾기
                    @SuppressWarnings("unchecked")
                    Map<String, Object> metadata = (Map<String, Object>) result.getOrDefault("metadata", new HashMap<>());
                    String answer = (String) metadata.getOrDefault("answer", "");

                    if (question != null && !question.isEmpty() && answer != null && !answer.isEmpty()) {
                        Map<String, Object> fewShot = new HashMap<>();
                        fewShot.put("input", question);
                        fewShot.put("output", answer);

                        // 메타데이터에 date 키가 있으면 포함
                        if (metadata.containsKey("date")) {
                            String date = (String) metadata.get("date");
                            fewShot.put("date", date);
                        }

                        // 메타데이터에 stats 키가 있으면 포함
                        if (metadata.containsKey("stats")) {
                            String stats = (String) metadata.get("stats");
                            fewShot.put("stats", stats);
                        }
                        
                        fewShots.add(fewShot);
                    }
                }
            }
            
            Map<String, Object> result = new HashMap<>();
            result.put("few_shots", fewShots);
            result.put("retrieve_time", retrieveTime);
            return result;
            
        } catch (Exception e) {
            log.error("[vector] few-shot 포맷팅 중 오류: {}", e.getMessage(), e);
            Map<String, Object> result = new HashMap<>();
            result.put("few_shots", new ArrayList<>());
            result.put("retrieve_time", 0.0);
            return result;
        }
    }

    /**
     * 주어진 쿼리에 대한 few-shot 예제들을 검색합니다.
     *
     * @param queryText 검색할 쿼리 텍스트
     * @param collectionName 컬렉션 이름 (null이면 기본값 사용)
     * @param topK 검색할 상위 결과 수
     * @param chainId 프로파일링용 chain_id
     * @return few-shot 예제 리스트와 검색 처리 시간
     */
    public Map<String, Object> getFewShots(String queryText, String collectionName, int topK, String chainId) {
        List<Map<String, Object>> results = queryVectorStore(queryText, collectionName, topK, chainId);
        return formatFewShots(results);
    }

    /**
     * 기본 컬렉션을 사용하여 few-shot 예제들을 검색합니다.
     *
     * @param queryText 검색할 쿼리 텍스트
     * @param topK 검색할 상위 결과 수
     * @return few-shot 예제 리스트와 검색 처리 시간
     */
    public Map<String, Object> getFewShots(String queryText, int topK) {
        return getFewShots(queryText, null, topK, null);
    }

    /**
     * 주어진 원본 노트에 대해 유사한 노트들을 벡터 API를 사용하여 검색합니다.
     *
     * @param originalNote 원본 노트
     * @param availableNotes 검색 대상 노트 리스트
     * @param topK 검색할 상위 결과 수
     * @param threshold 유사도 임계값
     * @return 유사한 노트 리스트
     */
    public List<String> getSimilarNotes(String originalNote, List<String> availableNotes, int topK, double threshold) {
        try {
            log.info("[vector] getSimilarNotes 시작 - 원본노트: {}, 대상노트수: {}", originalNote, availableNotes.size());

            if (availableNotes == null || availableNotes.isEmpty()) {
                log.warn("[vector] 검색 대상 노트가 없습니다");
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

            log.info("[vector] 노트 유사도 요청 페이로드: {}",
                    objectMapper.writeValueAsString(requestData));

            // API 호출
            ResponseEntity<String> response = restTemplate.postForEntity(
                    VECTOR_STORE_BASE_URL + "/pick", request, String.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                String responseBody = response.getBody();
                log.info("[vector] 노트 유사도 검색 완료 - 응답: {}", responseBody);

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
                                        log.info("[vector] 유사한 노트 발견: '{}' 점수: {}", candidate, score);
                                    }
                                }
                            }
                        }
                    }
                }

                log.info("[vector] getSimilarNotes 완료 - 임계값 {} 이상의 유사노트수: {}",
                        threshold, similarNotes.size());
                return similarNotes;

            } else {
                log.error("[vector] 노트 유사도 검색 실패 - 상태 코드: {}", response.getStatusCode());
                return new ArrayList<>();
            }

        } catch (Exception e) {
            log.error("[vector] getSimilarNotes 처리 중 오류: {}", e.getMessage(), e);
            return new ArrayList<>();
        }
    }

    /**
     * 벡터 DB에서 유사한 질문을 검색하고, 조건에 따라 선별된 결과를 반환합니다.
     *
     * @param queryText 검색할 쿼리 텍스트
     * @param topK 검색할 상위 결과 수
     * @param chainId 프로파일링용 chain_id
     * @return 선별된 문서 리스트
     */
    public List<String> getRecommend(String queryText, int topK, String chainId) {
        try {
            // 벡터 DB에서 검색
            List<Map<String, Object>> results = queryVectorStore(queryText, "hall_of_fame", topK, chainId);

            // document 추출 및 정규화
            String queryTextNormalized = queryText.replace(" ", "").trim();
            List<String> documents = new ArrayList<>();
            
            for (Map<String, Object> result : results) {
                if (result.containsKey("document")) {
                    String document = ((String) result.get("document")).trim();
                    documents.add(document);
                }
            }

            if (documents.isEmpty()) {
                return new ArrayList<>();
            }

            // 정규화된 문서 리스트 생성
            List<String> documentsNormalized = new ArrayList<>();
            for (String doc : documents) {
                documentsNormalized.add(doc.replace(" ", ""));
            }

            // query_text가 검색 결과에 있는지 확인
            int queryIndex = documentsNormalized.indexOf(queryTextNormalized);
            
            if (queryIndex != -1) {
                // query_text가 있으면 해당 항목을 제외한 나머지 중 앞의 3개 반환
                List<String> filteredDocs = new ArrayList<>();
                filteredDocs.addAll(documents.subList(0, queryIndex));
                filteredDocs.addAll(documents.subList(queryIndex + 1, documents.size()));
                return filteredDocs.subList(0, Math.min(3, filteredDocs.size()));
            } else {
                // query_text가 없으면 마지막 항목을 제외한 3개 반환
                return documents.subList(0, Math.min(3, documents.size()));
            }
            
        } catch (Exception e) {
            log.error("[vector] 추천 검색 중 오류: {}", e.getMessage(), e);
            return new ArrayList<>();
        }
    }
}
