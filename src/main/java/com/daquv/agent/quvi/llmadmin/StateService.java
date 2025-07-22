package com.daquv.agent.quvi.llmadmin;

import com.daquv.agent.entity.State;
import com.daquv.agent.quvi.entity.Node;
import com.daquv.agent.quvi.util.DatabaseProfilerAspect;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.repository.StateRepository;
import com.daquv.agent.quvi.repository.NodeRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import javax.servlet.http.HttpServletRequest;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@Service
@Transactional(readOnly = true)
public class StateService {

    private static final Logger log = LoggerFactory.getLogger(StateService.class);
    private final StateRepository stateRepository;
    private final NodeRepository nodeRepository;
    private final ObjectMapper objectMapper;

    @Autowired
    private RequestProfiler requestProfiler;

    public StateService(StateRepository stateRepository, NodeRepository nodeRepository, ObjectMapper objectMapper) {
        this.stateRepository = stateRepository;
        this.nodeRepository = nodeRepository;
        this.objectMapper = objectMapper;
    }

    /**
     * state 테이블에 새로운 상태 추가. 이전 상태에서 updates에 없는 값들은 보존
     *
     * @param traceId 트레이스 ID
     * @param updates 갱신할 상태값들의 Map
     * @return state 저장 성공 여부
     */
    @Transactional
    public boolean updateState(String traceId, Map<String, Object> updates) {
        log.info("updateState start - traceId: {}, updates: {}", traceId, updates);

        String chainId = getCurrentChainId();
        if (chainId != null) {
            DatabaseProfilerAspect.setWorkflowId(chainId);
            log.debug("StateService에서 chainId 설정: {}", chainId);
        }

        long startTime = System.currentTimeMillis();
        try {
            log.info("Trace 조회 시작 - traceId: {}", traceId);
            // 현재 trace의 직전 상태 조회
            List<State> currentStates = stateRepository.findLatestStatesByTraceId(traceId);
            Optional<State> currentStateOpt = currentStates.isEmpty() ? Optional.empty() : Optional.of(currentStates.get(0));

            Map<String, Object> newState = new HashMap<>();

            if (currentStateOpt.isPresent()) {
                State currentState = currentStateOpt.get();
                // 현재 상태에서 updates에 있는 키를 제외한 값들만 유지
                Map<String, Object> preservedState = new HashMap<>();
                preservedState.put("userQuestion", currentState.getUserQuestion());
                preservedState.put("selectedTable", currentState.getSelectedTable());
                preservedState.put("sqlQuery", currentState.getSqlQuery());
                preservedState.put("queryResult", currentState.getQueryResult());
                preservedState.put("finalAnswer", currentState.getFinalAnswer());
                preservedState.put("companyId", currentState.getCompanyId());
                preservedState.put("sqlError", currentState.getSqlError());
                preservedState.put("startDate", currentState.getStartDate());
                preservedState.put("endDate", currentState.getEndDate());
                preservedState.put("selectedApi", currentState.getSelectedApi());
                preservedState.put("fstringAnswer", currentState.getFstringAnswer());
                preservedState.put("totalRows", currentState.getTotalRows());
                preservedState.put("tablePipe", currentState.getTablePipe());

                // updates에 없는 값들만 유지
                for (Map.Entry<String, Object> entry : preservedState.entrySet()) {
                    if (!updates.containsKey(entry.getKey()) && entry.getValue() != null) {
                        newState.put(entry.getKey(), entry.getValue());
                    }
                }
            }

            // 보존된 상태에 새로운 업데이트 추가
            newState.putAll(updates);

            // Trace 조회
            Node node = nodeRepository.findById(traceId)
                    .orElseThrow(() -> new IllegalArgumentException("Trace not found: " + traceId));

            log.info("Trace 조회 완료 - trace: {}", node.getNodeId());

            State state = State.builder()
                    .node(node)
                    .userQuestion((String) newState.get("userQuestion"))
                    .selectedTable((String) newState.get("selectedTable"))
                    .sqlQuery((String) newState.get("sqlQuery"))
                    .queryResult(convertToJson(newState.get("queryResult")))
                    .finalAnswer((String) newState.get("finalAnswer"))
                    .companyId((String) newState.get("companyId"))
                    .sqlError((String) newState.get("sqlError"))
                    .startDate(convertToYYMMDD((String) newState.get("startDate")))
                    .endDate(convertToYYMMDD((String) newState.get("endDate")))
                    .selectedApi((String) newState.get("selectedApi"))
                    .fstringAnswer((String) newState.get("fstringAnswer"))
                    .tablePipe((String) newState.get("tablePipe"))
                    .totalRows((Integer) newState.get("totalRows"))
                    .build();

            log.info("State 객체 생성 완료 - state: {}", state);

            log.info("State 저장 시작 - stateRepository: {}", stateRepository.getClass().getSimpleName());
            try {
                State savedState = stateRepository.save(state);
                log.info("State 저장 완료 - savedState ID: {}", savedState != null ? savedState.getId() : "null");
            } catch (Exception e) {
                log.error("State 저장 실패 - 에러: {}", e.getMessage(), e);
                throw e;
            }

            log.info("updateState end - traceId: {}", traceId);
            return true;

        } catch (Exception e) {
            log.error("Error in updateState - traceId: {}, updates: {}", traceId, updates, e);
            throw new RuntimeException("Failed to update state", e);
        }
    }

    /**
     * 현재 trace와 같은 chain_id를 가진 직전 trace의 state를 조회
     *
     * @param traceId 트레이스 ID
     * @return 이전 상태 Map 또는 null (이전 state가 없는 경우)
     */
    public Map<String, Object> getLatestState(String traceId) {
        log.info("getLatestState - traceId: {}", traceId);

        String chainId = getCurrentChainId();
        long startTime = System.currentTimeMillis();
        try {
            List<State> states = stateRepository.findLatestStatesByTraceId(traceId);
            Optional<State> stateOpt = states.isEmpty() ? Optional.empty() : Optional.of(states.get(0));

            if (stateOpt.isPresent()) {
                log.info("No previous state found");
                return null;
            }

            State state = stateOpt.get();
            Map<String, Object> stateMap = new HashMap<>();

            stateMap.put("userQuestion", state.getUserQuestion());
            stateMap.put("selectedTable", state.getSelectedTable());
            stateMap.put("sqlQuery", state.getSqlQuery());
            stateMap.put("queryResult", parseJson(state.getQueryResult()));
            stateMap.put("finalAnswer", state.getFinalAnswer());
            stateMap.put("companyId", state.getCompanyId());
            stateMap.put("sqlError", state.getSqlError());
            stateMap.put("startDate", state.getStartDate());
            stateMap.put("endDate", state.getEndDate());
            stateMap.put("selectedApi", state.getSelectedApi());
            stateMap.put("fstringAnswer", state.getFstringAnswer());
            stateMap.put("totalRows", state.getTotalRows());
            stateMap.put("tablePipe", state.getTablePipe());

            return stateMap;

        } catch (Exception e) {
            log.error("Error in getLatestState - traceId: {}", traceId, e);
            return null;
        }
    }

    /**
     * 객체를 JSON 문자열로 변환
     */
    private String convertToJson(Object obj) {
        if (obj == null) {
            return "{}";
        }

        // 이미 문자열인 경우 JSON 유효성 검사
        if (obj instanceof String) {
            String str = (String) obj;
            if (str.trim().isEmpty()) {
                return "{}";
            }
            // 이미 JSON 형태인지 확인
            try {
                objectMapper.readTree(str);
                return str; // 이미 유효한 JSON이면 그대로 반환
            } catch (Exception e) {
                // JSON이 아니면 문자열을 JSON으로 변환
                try {
                    return objectMapper.writeValueAsString(obj);
                } catch (JsonProcessingException jsonEx) {
                    log.error("Error converting string to JSON", jsonEx);
                    return "{}";
                }
            }
        }

        // 객체인 경우 JSON으로 변환
        try {
            return objectMapper.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            log.error("Error converting object to JSON", e);
            return "{}";
        }
    }

    /**
     * JSON 문자열을 객체로 파싱
     */
    private Object parseJson(String json) {
        if (json == null || json.trim().isEmpty()) {
            return null;
        }
        try {
            return objectMapper.readValue(json, Object.class);
        } catch (JsonProcessingException e) {
            log.error("Error parsing JSON: {}", json, e);
            return json;
        }
    }



    /**
     * 트레이스 ID로 최신 상태 조회
     */
    public Optional<State> getLatestByTraceId(String traceId) {
        log.info("getLatestByTraceId - traceId: {}", traceId);
        return stateRepository.findLatestByTraceId(traceId);
    }

    /**
     * 체인 ID로 상태 목록 조회
     */
    public List<State> getStatesByChainId(String chainId) {
        log.info("getStatesByChainId - chainId: {}", chainId);
        return stateRepository.findByChainId(chainId);
    }

    /**
     * 선택된 API로 상태 목록 조회
     *
     * @param selectedApi 선택된 API
     * @return 상태 목록
     */
    public List<State> getStatesBySelectedApi(String selectedApi) {
        log.info("getStatesBySelectedApi - selectedApi: {}", selectedApi);
        return stateRepository.findBySelectedApi(selectedApi);
    }

    /**
     * table_pipe로 상태 목록 조회
     *
     * @param tablePipe 테이블 파이프
     * @return 상태 목록
     */
    public List<State> getStatesByTablePipe(String tablePipe) {
        log.info("getStatesByTablePipe - tablePipe: {}", tablePipe);
        return stateRepository.findByTablePipe(tablePipe);
    }

    /**
     * YYYYMMDD 형식의 날짜를 YYMMDD 형식으로 변환
     *
     * @param dateStr YYYYMMDD 형식의 날짜 문자열
     * @return YYMMDD 형식의 날짜 문자열 또는 null
     */
    private String convertToYYMMDD(String dateStr) {
        if (dateStr == null) {
            log.warn("Date string is null, returning null");
            return null;
        }

        if (dateStr.length() < 8) {
            log.warn("Date string '{}' is too short for YYYYMMDD format, returning as is", dateStr);
            return dateStr;
        }

        // YYYYMMDD (8자리)에서 YYMMDD (6자리)로 변환
        return dateStr.substring(2);
    }

    private String getCurrentChainId() {
        try {
            RequestAttributes requestAttributes = RequestContextHolder.getRequestAttributes();
            if (requestAttributes instanceof ServletRequestAttributes) {
                HttpServletRequest request = ((ServletRequestAttributes) requestAttributes).getRequest();

                Object chainIdAttr = request.getAttribute("chainId");
                if (chainIdAttr != null) {
                    return chainIdAttr.toString();
                }

                Object xChainIdAttr = request.getAttribute("X-Chain-Id");
                if (xChainIdAttr != null) {
                    return xChainIdAttr.toString();
                }
            }
        } catch (Exception e) {
            log.debug("getCurrentChainId 실패: {}", e.getMessage());
        }
        return null;
    }
}
