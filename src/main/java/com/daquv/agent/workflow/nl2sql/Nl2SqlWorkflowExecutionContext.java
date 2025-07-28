package com.daquv.agent.workflow.nl2sql;

import com.daquv.agent.quvi.llmadmin.NodeService;
import com.daquv.agent.workflow.nl2sql.node.*;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
@Slf4j
public class Nl2SqlWorkflowExecutionContext {

    @Autowired
    private Nl2SqlStateManager stateManager;

    @Autowired
    private NodeService nodeService;

    @Autowired
    private Nl2SqlDateCheckerNode nl2SqlDateCheckerNode;

    @Autowired
    private SafeguardNode safeguardNode;

    @Autowired
    private QueryExecutorNode queryExecutorNode;

    @Autowired
    private NextPageNode nextPageNode;

    @Autowired
    private RespondentNode respondentNode;

    @Autowired
    private NodataNode nodataNode;

    /**
     * NL2SQL 워크플로우 실행
     * 순서: DateChecker -> NextPage -> QueryExecutor -> (Safeguard) -> Respondent/Nodata
     */
    public void executeNl2SqlWorkflow(String workflowId) {
        log.info("=== NL2SQL 워크플로우 시작 - workflowId: {} ===", workflowId);

        try {
            Nl2SqlWorkflowState state = stateManager.getState(workflowId);
            if (state == null) {
                log.error("워크플로우 상태를 찾을 수 없습니다. workflowId: {}", workflowId);
                return;
            }

            // next_page 요청인 경우 NextPage부터 시작
            if ("next_page".equals(state.getUserQuestion())) {
                log.info("next_page 요청 감지 - NextPage 노드부터 시작");
                executeFromNextPage(state);
                return;
            }

            // 일반 워크플로우 실행 (DateChecker부터 시작)
            executeMainWorkflow(state);

        } catch (Exception e) {
            log.error("NL2SQL 워크플로우 실행 중 오류 발생 - workflowId: {}", workflowId, e);
            handleWorkflowError(workflowId, e);
        }

        log.info("=== NL2SQL 워크플로우 완료 - workflowId: {} ===", workflowId);
    }

    /**
     * HIL 이후 NL2SQL 워크플로우 재개 (날짜 명확화)
     */
    public void resumeNl2SqlWorkflowAfterDateClarification(String workflowId, String userInput) {
        log.info("=== HIL 이후 NL2SQL 워크플로우 재개 - workflowId: {}, userInput: {} ===", workflowId, userInput);

        try {
            Nl2SqlWorkflowState state = stateManager.getState(workflowId);
            if (state == null) {
                log.error("재개할 워크플로우 상태를 찾을 수 없습니다. workflowId: {}", workflowId);
                return;
            }

            // HIL 상태 확인
            if (!state.isHilRequired()) {
                log.warn("HIL이 필요하지 않은 상태입니다. workflowId: {}", workflowId);
                return;
            }

            // 사용자 입력을 질문에 추가
            String originalQuestion = state.getUserQuestion();
            String enhancedQuestion = originalQuestion + " " + userInput;
            state.setUserQuestion(enhancedQuestion);

            // HIL 상태 초기화
            state.clearHilState();

            log.info("사용자 질문 업데이트: {} -> {}", originalQuestion, enhancedQuestion);

            // 현재 노드부터 워크플로우 재개
            String currentNode = state.getCurrentNode();
            if ("date_checker".equals(currentNode)) {
                // DateChecker부터 다시 시작
                executeFromDateChecker(state);
            } else {
                // 전체 워크플로우 재시작
                executeMainWorkflow(state);
            }

        } catch (Exception e) {
            log.error("HIL 이후 NL2SQL 워크플로우 재개 중 오류 발생 - workflowId: {}", workflowId, e);
            handleWorkflowError(workflowId, e);
        }

        log.info("=== HIL 이후 NL2SQL 워크플로우 재개 완료 - workflowId: {} ===", workflowId);
    }

    /**
     * 메인 워크플로우 실행: DateChecker -> NextPage -> QueryExecutor -> Respondent/Nodata
     */
    private void executeMainWorkflow(Nl2SqlWorkflowState state) {
        // 1단계: DateChecker 실행
        if (!executeNode(state, nl2SqlDateCheckerNode, "DateChecker")) {
            return; // HIL 대기 또는 오류로 중단
        }

        // HIL이 필요한 경우 워크플로우 중단
        if (state.isHilRequired()) {
            log.info("HIL이 필요하여 워크플로우를 중단합니다.");
            return;
        }

        // 날짜 정보가 없는 경우 워크플로우 종료
        if (!state.hasDateInfo()) {
            log.warn("날짜 정보가 설정되지 않아 워크플로우를 종료합니다.");
            state.setFinalAnswer("죄송합니다. 날짜 정보를 확인할 수 없어 처리를 완료할 수 없습니다.");
            stateManager.updateState(state.getWorkflowId(), state);
            return;
        }

        // 2단계부터 계속 진행
        executeFromNextPage(state);
    }

    /**
     * DateChecker부터 워크플로우 실행 (HIL 재개용)
     */
    private void executeFromDateChecker(Nl2SqlWorkflowState state) {
        executeMainWorkflow(state);
    }

    /**
     * NextPage부터 워크플로우 실행: NextPage -> QueryExecutor -> Respondent/Nodata
     */
    private void executeFromNextPage(Nl2SqlWorkflowState state) {
        // 2단계: NextPage 실행 (next_page 요청이거나 일반 워크플로우의 2단계)
        if (!executeNode(state, nextPageNode, "NextPage")) {
            return;
        }

        // 3단계: QueryExecutor 실행 (Safeguard 포함)
        executeQueryWithSafeguard(state);

        // 4단계: 결과에 따른 분기 (Respondent/Nodata)
        executeFinalResponse(state);
    }

    /**
     * QueryExecutor 실행 (Safeguard와 함께, 최대 3회 시도)
     */
    private void executeQueryWithSafeguard(Nl2SqlWorkflowState state) {
        int maxAttempts = 3;

        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            log.info("쿼리 실행 시도 {}/{}", attempt, maxAttempts);

            // QueryExecutor 실행
            if (!executeNode(state, queryExecutorNode, "QueryExecutor")) {
                return; // 치명적 오류 발생
            }

            // 쿼리 실행 성공한 경우 루프 종료
            if ("success".equals(state.getQueryResultStatus())) {
                log.info("쿼리 실행 성공");
                return;
            }

            // 쿼리 오류가 발생한 경우 Safeguard 실행
            if (state.getQueryError() != null && state.getQueryError()) {
                log.warn("쿼리 오류 발생, Safeguard 노드로 이동");

                if (!executeNode(state, safeguardNode, "Safeguard")) {
                    return; // Safeguard 실행 실패
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
                // 다른 이유로 실패한 경우
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
        // 데이터 유무에 따른 분기
        if (state.getNoData() != null && state.getNoData()) {
            // 데이터 없음 처리
            log.info("데이터 없음 - Nodata 노드 실행");
            executeNode(state, nodataNode, "Nodata");
        } else {
            // 정상 응답 생성
            log.info("정상 응답 - Respondent 노드 실행");
            executeNode(state, respondentNode, "Respondent");
        }
    }

    /**
     * 노드 실행 헬퍼 메서드
     * @param state 워크플로우 상태
     * @param node 실행할 노드
     * @param nodeName 노드 이름 (로깅용)
     * @return 성공 여부 (false인 경우 워크플로우 중단 필요)
     */
    private boolean executeNode(Nl2SqlWorkflowState state, Nl2SqlWorkflowNode node, String nodeName) {
        String nodeId = null;
        try {
            log.info("=== {} 노드 실행 시작 ===", nodeName);

            // 노드 생성
            nodeId = nodeService.createNode(state.getWorkflowId(), node.getId());
            state.setNodeId(nodeId);

            // 노드 실행
            node.execute(state);

            // 노드 완료
            nodeService.completeNode(nodeId);

            // 상태 업데이트
            stateManager.updateState(state.getWorkflowId(), state);

            log.info("=== {} 노드 실행 완료 ===", nodeName);
            return true;

        } catch (Exception e) {
            log.error("{} 노드 실행 중 오류 발생", nodeName, e);

            // 오류 상태 기록
            if (nodeId != null) {
                try {
                    nodeService.markTraceError(nodeId);
                } catch (Exception traceError) {
                    log.error("{} Trace 오류 기록 실패: {}", nodeName, traceError.getMessage());
                }
            }

            // QueryExecutor의 경우 오류를 state에 반영하여 Safeguard가 처리할 수 있도록 함
            if ("QueryExecutor".equals(nodeName)) {
                state.setQueryError(true);
                state.setSqlError(e.getMessage());
                stateManager.updateState(state.getWorkflowId(), state);
                return true; // QueryExecutor 오류는 Safeguard에서 처리
            }

            // 다른 노드의 경우 치명적 오류로 처리
            return false;
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
}