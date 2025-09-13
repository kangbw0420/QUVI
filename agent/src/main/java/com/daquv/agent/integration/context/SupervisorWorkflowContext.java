package com.daquv.agent.integration.context;

import com.daquv.agent.integration.RunSql;
import com.daquv.agent.quvi.admin.WorkflowService;
import com.daquv.agent.quvi.util.NodeExecutor;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState;
import com.daquv.agent.workflow.killjoy.KilljoyWorkflowContext;
import com.daquv.agent.quvi.util.WorkflowStateManager;
import com.daquv.agent.quvi.util.ResumeUtil;
import com.daquv.agent.workflow.supervisor.SupervisorWorkflowState;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Component
@Slf4j
public class SupervisorWorkflowContext {

    @Autowired
    private WorkflowStateManager<SupervisorWorkflowState> stateManager;
    @Autowired
    private WorkflowService workflowService;
    @Autowired
    private NodeExecutor nodeExecutor;
    @Autowired
    private WorkflowStateManager<SemanticQueryWorkflowState> semanticQueryStateManager;
    @Autowired
    private SemanticQueryWorkflowContext semanticQueryWorkflowContext;
    @Autowired
    private KilljoyWorkflowContext killjoyWorkflowContext;
    @Autowired
    private RunSql runSql;

    /**
     * Supervisor 워크플로우 실행
     */
    public void executeSupervisorWorkflow(SupervisorWorkflowState supervisorState) {
        String workflowId = supervisorState.getWorkflowId();
        log.info("=== Supervisor 워크플로우 실행 시작 - workflowId: {} ===", workflowId);

        try {
            // 1. ClassifyJoyNode 실행 - JOY/FIN 분류
            nodeExecutor.executeNode("classifyJoyNode", supervisorState);

            // 2. SplitQuestionNode 실행 또는 JOY 워크플로우 직접 실행
            if ("YES".equals(supervisorState.getRelatedQuestion())) {
                // 3. 질문 쪼개기
                nodeExecutor.executeNode("splitQuestionNode", supervisorState);

                // 4. 쪼개진 질문별로 semanticquery 워크플로우 실행
                splitedSemanticQueryWorkflows(supervisorState);

                if (supervisorState.getHilRequired() != null && supervisorState.getHilRequired()) {
                    log.info("HIL이 필요하여 워크플로우 일시 중단: {}", supervisorState.getHilType());

                    // 상태 저장 후 return (workflowService.completeWorkflow 호출하지 않음)
                    stateManager.updateState(workflowId, supervisorState);

                    log.info("=== Supervisor 워크플로우 HIL 대기 상태 - workflowId: {} ===", workflowId);
                    return; // 여기서 중단
                }

                // 5. postProcessNode 실행
                nodeExecutor.executeNode("postProcessNode", supervisorState);

                // 6. RespondentNode 호출하여 최종 답변 생성
                nodeExecutor.executeNode("respondentNode", supervisorState);

                // 7. 최종 답변 생성
                String finalAnswer = supervisorState.getFinalAnswer();
                workflowService.completeWorkflow(workflowId, finalAnswer);
            } else {
                // JOY 워크플로우 직접 실행
                supervisorState = killjoyWorkflowContext.executeKilljoyWorkflow(
                        supervisorState
                );
            }

            // 변경된 State 저장
            stateManager.updateState(workflowId, supervisorState);

            log.info("=== Supervisor 워크플로우 실행 완료 - workflowId: {} ===", workflowId);

        } catch (Exception e) {
            log.error("Supervisor 워크플로우 실행 실패 - workflowId: {}", workflowId, e);
            stateManager.updateState(workflowId, supervisorState);
            throw e;
        }
    }

    /**
     * 각 분할된 질문에 대해 SemanticQuery 워크플로우 실행
     */
    private void splitedSemanticQueryWorkflows(SupervisorWorkflowState supervisorState) {
        String workflowId = supervisorState.getWorkflowId();
        if (supervisorState.getWorkflowExecutions() == null || supervisorState.getWorkflowExecutions().isEmpty()) {
            log.warn("실행할 워크플로우가 없습니다.");
            return;
        }

        // executionNo 순서대로 정렬하여 실행
        List<SupervisorWorkflowState.WorkflowExecution> sortedExecutions = supervisorState.getWorkflowExecutions()
                .stream()
                .sorted(Comparator.comparing(SupervisorWorkflowState.WorkflowExecution::getExecutionNo))
                .collect(Collectors.toList());

        for (SupervisorWorkflowState.WorkflowExecution execution : sortedExecutions) {
            try {
                // SemanticQuery State 생성 및 설정
                SemanticQueryWorkflowState semanticQueryState = semanticQueryStateManager.createState(workflowId, new SemanticQueryWorkflowState());
                semanticQueryState.setSplitedQuestion(execution.getSplitedQuestion());
                semanticQueryState.setUserInfo(supervisorState.getUserInfo());
                semanticQueryState.setWorkflowId(workflowId);
                semanticQueryState.setSessionId(supervisorState.getSessionId());
                semanticQueryState.setWebSocketSession(supervisorState.getWebSocketSession());

                // SemanticQuery 워크플로우 실행
                semanticQueryWorkflowContext.executeSemanticQueryWorkflow(semanticQueryState);

                // 실행 결과를 execution에 저장
                SemanticQueryWorkflowState resultState = semanticQueryStateManager.getState(workflowId);
                if (resultState != null) {

                    if (resultState.getDateClarificationNeeded() != null &&
                            resultState.getDateClarificationNeeded()) {

                        log.info("SemanticQuery에서 HIL 요청 발생, Supervisor 워크플로우 중단");
                        String hilMessage = generateDateClarificationMessage(execution.getSplitedQuestion());

                        // Supervisor 상태에 HIL 정보 전파
                        supervisorState.setHilRequired(true);
                        supervisorState.setHilType("date_clarification");
                        supervisorState.setFinalAnswer(hilMessage);

                        execution.setExecutionStatus("waiting");
                        return; // 즉시 중단
                    }

                    // SemanticQuery 결과 중 SQL/DSL/기간만 우선 매핑
                    execution.setExecutionQuery(resultState.getSqlQuery());
                    execution.setExecutionDsl(resultState.getDsl());
                    execution.setExecutionStartDate(resultState.getStartDate());
                    execution.setExecutionEndDate(resultState.getEndDate());

                    try {
                        runSql.executeSqlAndFillExecution(resultState.getSqlQuery(), supervisorState, execution);
                        execution.setExecutionStatus("completed");
                    } catch (Exception e) {
                        execution.setExecutionStatus("error");
                        execution.setExecutionError(true);
                        execution.setExecutionErrorMessage("SQL 생성 실패: " + e.getMessage());
                    }
                }

                log.info("SemanticQuery 워크플로우 실행 완료 - executionNo: {}, workflowId: {}",
                        execution.getExecutionNo(), workflowId);

            } catch (Exception e) {
                execution.setExecutionStatus("error");
                execution.setExecutionError(true);

                // semanticQueryState에서 errorAnswer를 가져와서 supervisorState의 finalAnswer로 설정
                SemanticQueryWorkflowState errorState = semanticQueryStateManager.getState(workflowId);
                if (errorState != null && errorState.getErrorAnswer() != null) {
                    supervisorState.setFinalAnswer(errorState.getErrorAnswer());
                } else {
                    // errorAnswer가 없다면 설정
                    supervisorState.setFinalAnswer("semanticQuery 실행 중 사전에 정의하지 않은 에러 발생: " + e.getMessage());
                }

                return;
            }
        }

        boolean hasData = supervisorState.getWorkflowExecutions().stream()
                .anyMatch(execution ->
                        "completed".equals(execution.getExecutionStatus()) &&
                                execution.getExecutionArrowData() != null &&
                                !execution.getExecutionArrowData().isEmpty()
                );

        if (!hasData) {
            log.info("모든 execution에서 데이터가 없음 - NoData 노드 실행");

            // SupervisorState에 noData 플래그 설정
            supervisorState.setNoData(true);

            try {
                // NoData 노드 실행
                nodeExecutor.executeNode("nodataNode", supervisorState);

                log.info("NoData 노드 실행 완료 - finalAnswer: {}", supervisorState.getFinalAnswer());

            } catch (Exception e) {
                log.error("NoData 노드 실행 실패", e);
                supervisorState.setFinalAnswer("데이터를 찾을 수 없어 답변을 생성할 수 없습니다.");
            } finally {
                supervisorState.setNoData(false);
            }
        } else {
            log.info("일부 execution에서 데이터 발견 - 정상 처리 진행");
        }
    }

    /**
     * HIL 이후 워크플로우 재개
     */
    public void resumeWorkflowAfterHil(String workflowId, Map<String, Object> userInput) {
        ResumeUtil.resumeSupervisorAfterHil(
                workflowId,
                userInput,
                () -> stateManager.getState(workflowId),
                (state) -> stateManager.updateState(workflowId, state),
                (nodeName, state) -> nodeExecutor.executeNode(nodeName, state)
        );
    }

    /**
     * SemanticQuery 결과로부터 execution 상태 업데이트
     */
    public void updateExecutionFromSemanticQueryResult(SupervisorWorkflowState.WorkflowExecution execution, String workflowId) {
        try {
            SemanticQueryWorkflowState semanticQueryState = semanticQueryStateManager.getState(workflowId);
            if (semanticQueryState != null) {
                execution.setExecutionQuery(semanticQueryState.getSqlQuery());
                execution.setExecutionDsl(semanticQueryState.getDsl());
                execution.setExecutionStartDate(semanticQueryState.getStartDate());
                execution.setExecutionEndDate(semanticQueryState.getEndDate());

                log.info("✅ Execution 상태 업데이트 완료 - executionNo: {}", execution.getExecutionNo());
            } else {
                log.warn("SemanticQuery 상태를 찾을 수 없습니다 - workflowId: {}", workflowId);
                execution.setExecutionStatus("error");
                execution.setExecutionError(true);
                execution.setExecutionErrorMessage("SemanticQuery 상태를 찾을 수 없습니다");
            }
        } catch (Exception e) {
            log.error("Execution 상태 업데이트 실패 - executionNo: {}, error: {}", execution.getExecutionNo(), e.getMessage());
            execution.setExecutionStatus("error");
            execution.setExecutionError(true);
            execution.setExecutionErrorMessage("상태 업데이트 실패: " + e.getMessage());
        }
    }

    /**
     * 날짜 명확화 요청 메시지 생성 (Supervisor용)
     */
    private String generateDateClarificationMessage(String userQuestion) {
        StringBuilder message = new StringBuilder();
        message.append("죄송합니다. 질문에서 날짜 범위를 명확히 파악하기 어렵습니다.\n\n");
        message.append("원하시는 분석 기간을 다음과 같은 형식으로 알려주세요:\n");
        message.append("- '2024년 1월부터 3월까지'\n");
        message.append("- '최근 3개월'\n");
        message.append("- '작년 전체'\n");
        message.append("- '2024년 상반기'\n\n");
        message.append("구체적인 기간을 입력해 주시면 정확한 분석을 도와드리겠습니다.");
        return message.toString();
    }
}