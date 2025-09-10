//  package com.daquv.agent.integration.ifagent;

//  import com.daquv.agent.workflow.dto.UserInfo;
//  import com.daquv.agent.integration.ifagent.IfExecutor;
//  import com.fasterxml.jackson.databind.JsonNode;
//  import com.fasterxml.jackson.databind.ObjectMapper;
//  import lombok.extern.slf4j.Slf4j;
//  import org.springframework.beans.factory.annotation.Autowired;
//  import org.springframework.beans.factory.annotation.Value;
//  import org.springframework.http.HttpEntity;
//  import org.springframework.http.HttpHeaders;
//  import org.springframework.http.MediaType;
//  import org.springframework.http.ResponseEntity;
//  import org.springframework.stereotype.Component;
//  import org.springframework.web.client.RestTemplate;

//  import java.util.HashMap;
//  import java.util.List;
//  import java.util.Map;

//  import static com.daquv.agent.integration.ifagent.IfExecutor.FETCH_ONE;

//  @Slf4j
//  @Component
//  public class IfQueryRequest {

//  private final RestTemplate restTemplate = new RestTemplate();

//  @Autowired
//  private IfExecutor ifExecutor;

//  @Value("${api.quvi-query}")
//  private String QUERY_API_BASE_URL;

//  @Value("${view-table.dialect}")
//  private String DIALECT;

//  @Value("${view-table.view-func}")
//  private String VIEW_FUNCTION;

//  /**
//  * SQL 쿼리가 반환할 총 행 수를 계산합니다.
//  *
//  * @param query SQL 쿼리
//  * @param limitValue 제한 값
//  * @return 총 행 수 (문자열로 반환)
//  */
//  public String countRows(String query, Integer limitValue, UserInfo userInfo)
//  {
//  try {
//  log.info("[query] count_rows API 호출 시작");
//  log.info("[query] 원본 쿼리: {}", query);
//  log.info("[query] 제한 값: {}", limitValue);

//  // 요청 데이터 구성
//  Map<String, Object> requestData = new HashMap<>();
//  requestData.put("query", query);
//  requestData.put("limit_value", limitValue);

//  log.info("[query] 요청 데이터: {}", requestData);

//  // HTTP 헤더 설정
//  HttpHeaders headers = new HttpHeaders();
//  headers.setContentType(MediaType.APPLICATION_JSON);

//  // HTTP 요청 생성
//  HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestData,
//  headers);

//  // API 호출
//  String apiUrl = QUERY_API_BASE_URL + "/pagination/count_rows";
//  log.info("[query] API URL: {}", apiUrl);

//  ResponseEntity<String> response = restTemplate.postForEntity(apiUrl, request,
//  String.class);

//  log.info("[query] API 응답 상태 코드: {}", response.getStatusCode());
//  log.info("[query] API 응답 본문: {}", response.getBody());

//  if (response.getStatusCode().is2xxSuccessful()) {
//  String result = response.getBody();
//  log.info("[query] count_rows API 호출 성공 - 결과: {}", result);

//  // 결과 파싱 시도
//  if (result != null && !result.trim().isEmpty()) {
//  try {
//  // JSON 응답에서 result 필드 추출
//  ObjectMapper objectMapper = new ObjectMapper();
//  JsonNode jsonNode = objectMapper.readTree(result);
//  String sqlQuery = jsonNode.get("result").asText();

//  log.info("[query] 추출된 SQL 쿼리: {}", sqlQuery);

//  // 실제 DB 쿼리 실행
//  // todo userInfo에서 가져와야함
//  List<Map<String, Object>> results = ifExecutor.executeIf(sqlQuery,
//  userInfo.getInttBizNo(),
//  userInfo.getInttCntrctId(), FETCH_ONE);
//  log.info("[query] COUNT 쿼리 실행 결과: {}", results);

//  if (!results.isEmpty()) {
//  Map<String, Object> firstRow = results.get(0);

//  // COUNT 쿼리는 보통 하나의 컬럼만 반환하므로 첫 번째 값 사용
//  Object countValue = firstRow.values().iterator().next();

//  if (countValue != null) {
//  Integer count = Integer.valueOf(countValue.toString());
//  log.info("[query] 최종 행 수: {}", count);
//  return count.toString();
//  } else {
//  log.warn("[query] COUNT 값이 null입니다");
//  return "0";
//  }
//  } else {
//  log.warn("[query] COUNT 쿼리 결과가 비어있습니다");
//  return "0";
//  }
//  } catch (Exception e) {
//  log.error("[query] COUNT 쿼리 실행 중 오류: {}", e.getMessage(), e);
//  return "0";
//  }
//  } else {
//  log.warn("[query] 빈 결과 반환됨");
//  return "0";
//  }
//  } else {
//  log.error("[query] count_rows API 호출 실패 - 상태 코드: {}",
//  response.getStatusCode());
//  return "행 수 계산 중 오류가 발생했습니다.";
//  }

//  } catch (Exception e) {
//  log.error("[query] count_rows API 호출 중 예외 발생: {}", e.getMessage(), e);
//  return "행 수 계산 중 오류가 발생했습니다: " + e.getMessage();
//  }
//  }
//  }