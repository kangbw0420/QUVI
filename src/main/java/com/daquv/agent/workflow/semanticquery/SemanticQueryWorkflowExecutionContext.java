package com.daquv.agent.workflow.semanticquery;

import com.daquv.agent.quvi.llmadmin.NodeService;
import com.daquv.agent.quvi.llmadmin.WorkflowService;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.daquv.agent.workflow.semanticquery.utils.SemanticQueryExecutorResultHandler;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Component
@Slf4j
public class SemanticQueryWorkflowExecutionContext {

    @Autowired
    private SemanticQueryStateManager stateManager;

    @Autowired
    private ApplicationContext applicationContext;

    @Autowired
    private NodeService nodeService;

    @Autowired
    private SemanticQueryExecutorResultHandler executorResultHandler;

    @Autowired
    private WorkflowService workflowService;

    /**
     * SemanticQuery 워크플로우 실행
     * - DSL 경로: extractMetrics -> extractFilter -> manipulation -> dsl2sql -> runSql -> postProcess -> respondent
     */
    public void executeSemanticQueryWorkflow(String workflowId) {
        SemanticQueryWorkflowState state = stateManager.getState(workflowId);
        if (state == null) {
            throw new IllegalStateException("Workflow ID에 해당하는 State를 찾을 수 없습니다: " + workflowId);
        }

        log.info("=== SemanticQuery DSL 워크플로우 실행 시작 - workflowId: {} ===", workflowId);

        try {
            // 0. DateChecker Node - 날짜 정보 확인 및 HIL 처리
            executeNode("dateCheckerNode", state);

            // HIL 상태 체크 - 날짜 명확화가 필요한 경우 워크플로우 중단
            if (state.getDateClarificationNeeded() != null && state.getDateClarificationNeeded()) {
                log.info("SemanticQuery: 날짜 명확화가 필요하여 워크플로우를 대기 상태로 전환합니다.");

                saveStateToDatabase(state.getNodeId(), state);

                log.info("=== SemanticQuery DSL 워크플로우 대기 상태 - workflowId: {} ===", workflowId);
                return; // 워크플로우 중단, 사용자 입력 대기
            }

            // 1. ExtractMetrics Node - 메트릭과 그룹바이 추출
            executeNode("extractMetricsNode", state);

            // SemanticQueryExecution이 생성되었는지 확인
            if (state.getSemanticQueryExecutionMap() == null || state.getSemanticQueryExecutionMap().isEmpty()) {
                log.error("SemanticQuery: ExtractMetrics에서 DSL 추출 실패");
                return;
            }

            // 2. ExtractFilter Node - 필터 추출 및 적용
            executeNode("extractFilterNode", state);

            // 3. Manipulation Node - order by/limit 추출 및 커스텀 조작
            executeNode("manipulationNode", state);

            // 4. Dsl2Sql Node - DSL을 SQL로 변환
            executeNode("dsl2SqlNode", state);

            // SQL 변환 실패 확인
            boolean hasSqlQueries = false;
            for (SemanticQueryWorkflowState.SemanticQueryExecution execution : state.getSemanticQueryExecutionMap().values()) {
                if (execution.getSqlQuery() != null && !execution.getSqlQuery().isEmpty()) {
                    hasSqlQueries = true;
                    break;
                }
            }

            if (!hasSqlQueries) {
                log.error("SemanticQuery: DSL to SQL 변환에 실패했습니다.");
                return;
            }

            // 5. RunSql Node - SQL 실행 및 결과 저장
            executeNode("runSqlNode", state);

            // 6. PostProcess Node (쿼리 실행에 성공한 경우만)
            boolean hasValidResults = false;
            for (SemanticQueryWorkflowState.SemanticQueryExecution execution : state.getSemanticQueryExecutionMap().values()) {
                if ("success".equals(execution.getQueryResultStatus())) {
                    hasValidResults = true;
                    break;
                }
            }

            if (hasValidResults) {
                executeNode("postProcessNode", state);
            } else {
                log.warn("SemanticQuery: 모든 쿼리 실행이 실패하여 후처리를 건너뜁니다.");
            }

            // 7. Executor 결과 처리
            log.info("SemanticQuery: Executor 결과 처리 시작");
            executorResultHandler.handleSemanticQueryExecutorResults(state);

            // 변경된 State 저장
            stateManager.updateState(workflowId, state);

            log.info("=== SemanticQuery DSL 워크플로우 실행 완료 - workflowId: {} ===", workflowId);

        } catch (Exception e) {
            log.error("SemanticQuery DSL 워크플로우 실행 실패 - workflowId: {}", workflowId, e);
            stateManager.updateState(workflowId, state);
            throw e;
        }
    }

    /**
     * HIL 이후 워크플로우 재개 (날짜 정보가 명확해진 후)
     */
    public void resumeSemanticQueryWorkflowAfterDateClarification(String workflowId, String userInput) {
        SemanticQueryWorkflowState state = stateManager.getState(workflowId);
        if (state == null) {
            throw new IllegalStateException("Workflow ID에 해당하는 State를 찾을 수 없습니다: " + workflowId);
        }

        log.info("=== SemanticQuery 워크플로우 재개 - 날짜 명확화 후 - workflowId: {} ===", workflowId);

        try {
            // 사용자 입력을 기존 질문에 추가
            String enhancedQuestion = state.getUserQuestion() + " " + userInput;
            state.setUserQuestion(enhancedQuestion);

            // HIL 상태 초기화
            state.clearHilState();

            // 날짜 체커 노드부터 재실행
            executeNode("dateCheckerNode", state);

            // 여전히 날짜가 불명확한 경우
            if (state.getDateClarificationNeeded() != null && state.getDateClarificationNeeded()) {
                log.warn("SemanticQuery: 추가 입력 후에도 날짜가 불명확합니다.");
                workflowService.waitingWorkflow(workflowId, state.getFinalAnswer());
                stateManager.updateState(workflowId, state);
                return;
            }

            // 날짜가 명확해진 경우 이후 단계 진행
            executeNode("manipulationNode", state);
            executeNode("dsl2SqlNode", state);

            // SQL 변환 확인
            boolean hasSqlQueries = false;
            for (SemanticQueryWorkflowState.SemanticQueryExecution execution : state.getSemanticQueryExecutionMap().values()) {
                if (execution.getSqlQuery() != null && !execution.getSqlQuery().isEmpty()) {
                    hasSqlQueries = true;
                    break;
                }
            }

            if (!hasSqlQueries) {
                log.error("SemanticQuery: DSL to SQL 변환에 실패했습니다.");
                return;
            }

            executeNode("runSqlNode", state);

            // 쿼리 실행 결과 확인
            boolean hasValidResults = false;
            for (SemanticQueryWorkflowState.SemanticQueryExecution execution : state.getSemanticQueryExecutionMap().values()) {
                if ("success".equals(execution.getQueryResultStatus())) {
                    hasValidResults = true;
                    break;
                }
            }

            if (hasValidResults) {
                executeNode("postProcessNode", state);
                executeNode("semanticQueryRespondentNode", state);
                log.info("SemanticQuery: 재개된 워크플로우 완료");
            } else {
                log.warn("SemanticQuery: 재개된 워크플로우에서 쿼리 실행 실패");
            }

            // 워크플로우 완료 상태로 변경
            workflowService.completeWorkflow(workflowId, state.getFinalAnswer());
            stateManager.updateState(workflowId, state);

            log.info("=== SemanticQuery 워크플로우 재개 완료 - workflowId: {} ===", workflowId);

        } catch (Exception e) {
            log.error("SemanticQuery 워크플로우 재개 실패 - workflowId: {}", workflowId, e);
            stateManager.updateState(workflowId, state);
            throw e;
        }
    }

    /**
     * 개별 노드 실행 (State 직접 주입 + Trace/State 처리)
     */
    public void executeNode(String nodeBeanName, SemanticQueryWorkflowState state) {
        String nodeId = null;

        log.info("SemanticQuery node executing: {} - state: {}", nodeBeanName, state.getWorkflowId());

        try {
            Object nodeBean = applicationContext.getBean(nodeBeanName);

            if (nodeBean instanceof SemanticQueryWorkflowNode) {
                SemanticQueryWorkflowNode node = (SemanticQueryWorkflowNode) nodeBean;

                // 1. Node 생성
                nodeId = nodeService.createNode(state.getWorkflowId(), node.getId());
                state.setNodeId(nodeId);

                // 2. 노드 실행
                node.execute(state);

                // 3. Trace 완료
                nodeService.completeNode(nodeId);

                log.info("State 어떻게 되어있니 {}", state);

                // 4. State DB 저장 (현재 state의 모든 필드를 저장)
                saveStateToDatabase(nodeId, state);

                log.debug("SemanticQuery 노드 {} 실행 완료 - traceId: {}", nodeBeanName, nodeId);

            } else {
                throw new IllegalArgumentException("지원하지 않는 SemanticQuery 노드 타입: " + nodeBeanName);
            }

        } catch (Exception e) {
            log.error("SemanticQuery 노드 실행 실패: {} - workflowId: {}", nodeBeanName, state.getWorkflowId(), e);

            // Trace 오류 상태로 변경
            if (nodeId != null) {
                try {
                    nodeService.markTraceError(nodeId);
                } catch (Exception traceError) {
                    log.error("SemanticQuery Trace 오류 기록 실패: {}", traceError.getMessage());
                }
            }

            throw e;
        }
    }

    /**
     * SemanticQuery State를 DB에 저장
     */
    private void saveStateToDatabase(String traceId, SemanticQueryWorkflowState state) {
        try {
            Map<String, Object> stateMap = new HashMap<>();

            // 기본 필드들 처리
            addStringFieldIfNotEmpty(stateMap, "userQuestion", state.getUserQuestion());
            addStringFieldIfNotEmpty(stateMap, "workflowId", state.getWorkflowId());
            addStringFieldIfNotEmpty(stateMap, "nodeId", state.getNodeId());

            // UserInfo에서 companyId 추가
            if (state.getUserInfo() != null) {
                addStringFieldIfNotEmpty(stateMap, "companyId", state.getUserInfo().getCompanyId());
            }

            // SemanticQueryExecutionMap 처리
            if (state.getSemanticQueryExecutionMap() != null && !state.getSemanticQueryExecutionMap().isEmpty()) {
                Map<String, Object> executionSummary = new HashMap<>();

                state.getSemanticQueryExecutionMap().forEach((entity, execution) -> {

                    Map<String, Object> executionData = new HashMap<>();

                    // SQL 쿼리들
                    addMapFieldIfNotEmpty(executionData, "sqlQuery", execution.getSqlQuery());

                    // 쿼리 결과들
                    addMapFieldIfNotEmpty(executionData, "queryResult", execution.getQueryResult());
                    addCollectionFieldIfNotEmpty(executionData, "postQueryResult", execution.getPostQueryResult());

                    // 문자열 필드들
                    addStringFieldIfNotEmpty(executionData, "sqlError", execution.getSqlError());
                    addStringFieldIfNotEmpty(executionData, "fString", execution.getFString());
                    addStringFieldIfNotEmpty(executionData, "finalAnswer", execution.getFinalAnswer());
                    addStringFieldIfNotEmpty(executionData, "tablePipe", execution.getTablePipe());
                    addStringFieldIfNotEmpty(executionData, "startDate", execution.getStartDate());
                    addStringFieldIfNotEmpty(executionData, "endDate", execution.getEndDate());
                    addStringFieldIfNotEmpty(executionData, "queryResultStatus", execution.getQueryResultStatus());

                    // 컬렉션 필드들
                    addMapFieldIfNotEmpty(executionData, "totalRows", execution.getTotalRows());
                    addCollectionFieldIfNotEmpty(executionData, "queryResultList", execution.getQueryResultList());

                    // Boolean 필드들 (기본값이 아닌 경우만 저장)
                    addBooleanFieldIfNotDefault(executionData, "noData", execution.getNoData(), false);
                    addBooleanFieldIfNotDefault(executionData, "futureDate", execution.getFutureDate(), false);
                    addBooleanFieldIfNotDefault(executionData, "invalidDate", execution.getInvalidDate(), false);
                    addBooleanFieldIfNotDefault(executionData, "queryError", execution.getQueryError(), false);
                    addBooleanFieldIfNotDefault(executionData, "queryChanged", execution.getQueryChanged(), false);
                    addBooleanFieldIfNotDefault(executionData, "hasNext", execution.getHasNext(), false);
                    addBooleanFieldIfNotDefault(executionData, "noteChanged", execution.getNoteChanged(), false);

                    // Integer 필드들 (기본값이 아닌 경우만 저장)
                    addIntegerFieldIfNotDefault(executionData, "safeCount", execution.getSafeCount(), 0);

                    // VectorNotes 처리
                    if (execution.getVectorNotes() != null) {
                        executionData.put("vectorNotes", execution.getVectorNotes());
                    }

                    // DSL 처리
                    if (execution.getDsl() != null && !execution.getDsl().isEmpty()) {
                        executionData.put("dsl", execution.getDsl());
                    }

                    if (!executionData.isEmpty()) {
                        executionSummary.put(entity, executionData);
                    }
                });
                
                if (!executionSummary.isEmpty()) {
                    stateMap.put("semanticQueryExecutions", executionSummary);
                }
            }

            // JSON 변환 및 저장
            if (!stateMap.isEmpty()) {
                ObjectMapper objectMapper = new ObjectMapper();
                String stateJson = objectMapper.writeValueAsString(stateMap);
                nodeService.updateNodeStateJson(traceId, stateJson);
                log.debug("SemanticQuery Node state JSON 저장 완료 - traceId: {}, fields: {}", traceId, stateMap.keySet());
            } else {
                log.debug("SemanticQuery Node state가 비어있어 저장하지 않음 - traceId: {}", traceId);
            }

        } catch (Exception e) {
            log.error("SemanticQuery State DB 저장 실패 - traceId: {}", traceId, e);
            // State 저장 실패는 워크플로우를 중단하지 않음
        }
    }

    /**
     * 문자열 필드가 null이 아니고 비어있지 않으면 Map에 추가
     */
    private void addStringFieldIfNotEmpty(Map<String, Object> map, String key, String value) {
        if (value != null && !value.trim().isEmpty()) {
            map.put(key, value.trim());
        }
    }

    /**
     * 컬렉션 필드가 null이 아니고 비어있지 않으면 Map에 추가
     */
    private void addCollectionFieldIfNotEmpty(Map<String, Object> map, String key, Object collection) {
        if (collection instanceof List) {
            List<?> list = (List<?>) collection;
            if (!list.isEmpty()) {
                map.put(key, collection);
            }
        } else if (collection instanceof Map) {
            Map<?, ?> mapValue = (Map<?, ?>) collection;
            if (!mapValue.isEmpty()) {
                map.put(key, collection);
            }
        }
    }

    /**
     * Map 필드가 null이 아니고 비어있지 않으면 Map에 추가
     */
    private void addMapFieldIfNotEmpty(Map<String, Object> map, String key, Map<?, ?> mapValue) {
        if (mapValue != null && !mapValue.isEmpty()) {
            map.put(key, mapValue);
        }
    }

    /**
     * Boolean 필드가 기본값과 다르면 Map에 추가
     */
    private void addBooleanFieldIfNotDefault(Map<String, Object> map, String key, Boolean value, Boolean defaultValue) {
        if (value != null && !value.equals(defaultValue)) {
            map.put(key, value);
        }
    }

    /**
     * Integer 필드가 기본값과 다르면 Map에 추가
     */
    private void addIntegerFieldIfNotDefault(Map<String, Object> map, String key, Integer value, Integer defaultValue) {
        if (value != null && !value.equals(defaultValue)) {
            map.put(key, value);
        }
    }
}