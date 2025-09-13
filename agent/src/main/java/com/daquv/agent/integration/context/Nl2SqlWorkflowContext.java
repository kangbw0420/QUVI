package com.daquv.agent.integration.context;

import com.daquv.agent.quvi.llmadmin.NodeService;
import com.daquv.agent.quvi.util.WorkflowNode;
import com.daquv.agent.quvi.util.WorkflowStateManager;
import com.daquv.agent.workflow.nl2sql.Nl2SqlWorkflowState;
import com.daquv.agent.workflow.nl2sql.node.*;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

@Component
@Slf4j
public class Nl2SqlWorkflowContext {

    @Autowired
    private WorkflowStateManager<Nl2SqlWorkflowState> stateManager;

    @Autowired
    private NodeService nodeService;

    @Autowired
    private DaterNode daterNode;

    @Autowired
    private Nl2sqlNode nl2sqlNode;

    @Autowired
    private QueryExecutorNode queryExecutorNode;

    @Autowired
    private SafeguardNode safeguardNode;

    // @Autowired
    // private NextPageNode nextPageNode;

    @Autowired
    private CommanderNode commanderNode;

    @Autowired
    private RespondentNode respondentNode;

    @Autowired
    private NodataNode nodataNode;

    /**
     * NL2SQL 워크플로우 실행
     * - 일반 요청: Dater -> Nl2sql -> QueryExecutor -> (Safeguard) -> Respondent/Nodata
     * - next_page 요청: NextPage -> Respondent/Nodata
     */
    public void executeNl2SqlWorkflow(Nl2SqlWorkflowState state) {
        if (state == null) {
            throw new IllegalStateException("State가 null입니다.");
        }
        
        String workflowId = state.getWorkflowId();
        log.info("=== NL2SQL 워크플로우 시작 - workflowId: {} ===", workflowId);

        try {

            // next_page 요청인 경우: 기존 SQL 재사용하여 페이지네이션만 처리
            // if ("next_page".equals(state.getUserQuestion())) {
            //     log.info("next_page 요청 감지 - 페이지네이션 처리");
            //     executeNode(nextPageNode, state, "NextPage");
            //     executeFinalResponse(state);
            //     return;
            // }

            // 0. Commander 실행 (테이블 선택)
            executeNode(commanderNode, state, "Commander");

            // 테이블 선택 확인
            if (state.getSelectedTable() == null || state.getSelectedTable().trim().isEmpty()) {
                log.error("테이블 선택에 실패했습니다.");
                state.setFinalAnswer("죄송합니다. 적절한 데이터 테이블을 찾을 수 없습니다.");
                stateManager.updateState(state.getWorkflowId(), state);
                return;
            }

            // 일반 워크플로우 실행
            // 1. Dater 실행 (HIL 없는 버전)
            executeNode(daterNode, state, "Dater");

            // 날짜 정보가 없는 경우 워크플로우 종료
            if (!state.hasDateInfo()) {
                log.warn("날짜 정보가 설정되지 않아 워크플로우를 종료합니다.");
                state.setFinalAnswer("죄송합니다. 날짜 정보를 확인할 수 없어 처리를 완료할 수 없습니다.");
                stateManager.updateState(state.getWorkflowId(), state);
                return;
            }

            // 2. Nl2sql 실행 (SQL 생성)
            executeNode(nl2sqlNode, state, "Nl2sql");

            // SQL 생성 확인
            if (state.getSqlQuery() == null || state.getSqlQuery().trim().isEmpty()) {
                log.error("SQL 쿼리가 생성되지 않았습니다.");
                state.setFinalAnswer("죄송합니다. SQL 쿼리를 생성할 수 없습니다.");
                stateManager.updateState(state.getWorkflowId(), state);
                return;
            }

            // 3. QueryExecutor 실행 (Safeguard와 함께 최대 3회 시도)
            executeQueryWithSafeguard(state);

            // 4. 최종 응답 생성
            executeFinalResponse(state);

            log.info("=== NL2SQL 워크플로우 완료 - workflowId: {} ===", workflowId);

        } catch (Exception e) {
            log.error("NL2SQL 워크플로우 실행 중 오류 발생 - workflowId: {}", workflowId, e);
            handleWorkflowError(workflowId, e);
        }
    }

    /**
     * HIL 이후 NL2SQL 워크플로우 재개 (날짜 명확화) - HIL 미사용 버전에서는 사용하지 않음
     */
    public void resumeNl2SqlWorkflowAfterDateClarification(Nl2SqlWorkflowState state, String userInput) {
        if (state == null) {
            throw new IllegalStateException("State가 null입니다.");
        }
        
        String workflowId = state.getWorkflowId();
        log.info("=== HIL 이후 NL2SQL 워크플로우 재개 - workflowId: {}, userInput: {} ===", workflowId, userInput);
        log.warn("현재 HIL 미사용 버전으로 설정되어 있어 재개 기능을 사용할 수 없습니다.");

        try {

            // 사용자 입력을 질문에 추가하여 다시 처리
            String originalQuestion = state.getUserQuestion();
            String enhancedQuestion = originalQuestion + " " + userInput;
            state.setUserQuestion(enhancedQuestion);

            log.info("사용자 질문 업데이트: {} -> {}", originalQuestion, enhancedQuestion);

            // Dater부터 다시 실행
            executeNode(daterNode, state, "dater");

            // 날짜 정보 확인
            if (!state.hasDateInfo()) {
                log.warn("재개 후에도 날짜 정보가 없습니다.");
                state.setFinalAnswer("죄송합니다. 날짜 정보를 확인할 수 없어 처리를 완료할 수 없습니다.");
                stateManager.updateState(state.getWorkflowId(), state);
                return;
            }

            // Nl2sql부터 이후 단계 진행
            executeNode(nl2sqlNode, state, "Nl2sql");

            if (state.getSqlQuery() == null || state.getSqlQuery().trim().isEmpty()) {
                log.error("재개 후 SQL 쿼리 생성 실패");
                state.setFinalAnswer("죄송합니다. SQL 쿼리를 생성할 수 없습니다.");
                stateManager.updateState(state.getWorkflowId(), state);
                return;
            }

            executeQueryWithSafeguard(state);
            executeFinalResponse(state);

            log.info("=== HIL 이후 NL2SQL 워크플로우 재개 완료 - workflowId: {} ===", workflowId);

        } catch (Exception e) {
            log.error("HIL 이후 NL2SQL 워크플로우 재개 중 오류 발생 - workflowId: {}", workflowId, e);
            handleWorkflowError(workflowId, e);
        }
    }

    /**
     * QueryExecutor 실행 (Safeguard와 함께, 최대 3회 시도)
     */
    private void executeQueryWithSafeguard(Nl2SqlWorkflowState state) {
        int maxAttempts = 3;

        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            log.info("쿼리 실행 시도 {}/{}", attempt, maxAttempts);

            // QueryExecutor 실행
            try {
                executeNode(queryExecutorNode, state, "QueryExecutor");
            } catch (Exception e) {
                log.error("QueryExecutor 실행 실패: {}", e.getMessage());
                state.setQueryError(true);
                state.setSqlError(e.getMessage());
            }

            // 쿼리 실행 성공한 경우 루프 종료
            if ("success".equals(state.getQueryResultStatus())) {
                log.info("쿼리 실행 성공");
                return;
            }

            // 쿼리 오류가 발생한 경우 Safeguard 실행
            if (state.getQueryError() != null && state.getQueryError()) {
                log.warn("쿼리 오류 발생, Safeguard 노드 실행");

                try {
                    executeNode(safeguardNode, state, "Safeguard");
                } catch (Exception e) {
                    log.error("Safeguard 실행 실패: {}", e.getMessage());
                    break;
                }

                // Safeguard가 쿼리를 수정했는지 확인
                if (state.getQueryChanged() != null && state.getQueryChanged()) {
                    log.info("Safeguard가 쿼리를 수정했습니다. 다음 시도로 진행");
                    // 오류 상태 초기화
                    state.setQueryError(false);
                    state.setSqlError(null);
                    state.setQueryChanged(false);
                    continue; // 다음 시도
                } else {
                    log.error("Safeguard가 쿼리를 수정하지 못했습니다.");
                    break; // 루프 종료
                }
            } else {
                log.warn("쿼리 실행이 실패했지만 QueryError 플래그가 설정되지 않음");
                break;
            }
        }

        log.warn("최대 시도 횟수 {} 회를 초과했거나 복구 불가능한 오류 발생", maxAttempts);
    }

    /**
     * 최종 응답 생성 (Respondent 또는 Nodata)
     */
    private void executeFinalResponse(Nl2SqlWorkflowState state) {
        if (state.getNoData() != null && state.getNoData()) {
            log.info("데이터 없음 - Nodata 노드 실행");
            executeNode(nodataNode, state, "Nodata");
        } else {
            log.info("정상 응답 - Respondent 노드 실행");
            executeNode(respondentNode, state, "Respondent");
        }
    }

    /**
     * 개별 노드 실행
     */
    private void executeNode(WorkflowNode<Nl2SqlWorkflowState> node, Nl2SqlWorkflowState state, String nodeName) {
        String nodeId = null;

        log.info("NL2SQL node executing: {} - state: {}", nodeName, state.getWorkflowId());

        try {
            // 1. Node 생성
            nodeId = nodeService.createNode(state.getWorkflowId(), node.getId());
            state.setNodeId(nodeId);

            // 2. 노드 실행
            node.execute(state);

            // 3. Trace 완료
            nodeService.completeNode(nodeId);

            // 4. State DB 저장
            saveStateToDatabase(nodeId, state);

            log.debug("NL2SQL 노드 {} 실행 완료 - nodeId: {}", nodeName, nodeId);

        } catch (Exception e) {
            log.error("NL2SQL 노드 실행 실패: {} - workflowId: {}", nodeName, state.getWorkflowId(), e);

            // Trace 오류 상태로 변경
            if (nodeId != null) {
                try {
                    nodeService.markTraceError(nodeId);
                } catch (Exception traceError) {
                    log.error("NL2SQL Trace 오류 기록 실패: {}", traceError.getMessage());
                }
            }

            throw e;
        }
    }

    /**
     * 워크플로우 오류 처리
     */
    private void handleWorkflowError(String workflowId, Exception e) {
        try {
            Nl2SqlWorkflowState state = stateManager.getState(workflowId);
            if (state == null) {
                log.error("오류 처리 중 상태를 찾을 수 없습니다. workflowId: {}", workflowId);
                return;
            }

            String errorMessage = "죄송합니다. 처리 중 오류가 발생했습니다: " + e.getMessage();
            state.setFinalAnswer(errorMessage);
            state.setQueryResultStatus("failed");

            stateManager.updateState(workflowId, state);

        } catch (Exception ex) {
            log.error("워크플로우 오류 처리 중 추가 오류 발생 - workflowId: {}", workflowId, ex);
        }
    }

    /**
     * State를 DB에 저장
     */
    private void saveStateToDatabase(String nodeId, Nl2SqlWorkflowState state) {
        try {
            ObjectMapper objectMapper = new ObjectMapper();
            objectMapper.setSerializationInclusion(JsonInclude.Include.NON_NULL);

            @SuppressWarnings("unchecked")
            String stateJson = objectMapper.writeValueAsString(state);

            nodeService.updateNodeStateJson(nodeId, stateJson);

        } catch (Exception e) {
            log.error("State DB 저장 실패 - traceId: {}", nodeId, e);
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
}