package com.daquv.agent.workflow.semanticquery.utils;

import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowExecutionContext;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Component;

import java.util.Map;

@Component
@Slf4j
public class SemanticQueryExecutorResultHandler {

    @Autowired
    private ApplicationContext applicationContext;

    private SemanticQueryWorkflowExecutionContext getExecutionContext() {
        return applicationContext.getBean(SemanticQueryWorkflowExecutionContext.class);
    }

    /**
     * SemanticQuery Executor 결과 처리 로직 (기존 DEFAULT 워크플로우 로직 적용)
     */
    public void handleSemanticQueryExecutorResults(SemanticQueryWorkflowState state) {
        Map<String, SemanticQueryWorkflowState.SemanticQueryExecution> executionMap = state.getSemanticQueryExecutionMap();

        if (executionMap == null || executionMap.isEmpty()) {
            log.error("No SemanticQueryExecution found in state");
            return;
        }

        boolean hasValidResults = false;
        boolean hasNoData = true;
        boolean hasQueryError = false;
        boolean hasInvalidDate = false;
        int maxSafeCount = 0;

        // 모든 execution의 상태를 종합적으로 확인
        for (Map.Entry<String, SemanticQueryWorkflowState.SemanticQueryExecution> entry : executionMap.entrySet()) {
            String entity = entry.getKey();
            SemanticQueryWorkflowState.SemanticQueryExecution execution = entry.getValue();

            log.debug("Checking execution results for entity: {}", entity);

            // SQL 쿼리가 있는지 확인
            if (execution.getSqlQuery() == null || execution.getSqlQuery().isEmpty()) {
                execution.setQueryResultStatus("failed");
                execution.setSqlError("SQL 쿼리가 생성되지 않았습니다.");
                log.error("SQL 쿼리 생성 실패 for entity: {}", entity);
                continue;
            }

            // Invalid date 체크 (최우선)
            if (execution.getInvalidDate() != null && execution.getInvalidDate()) {
                hasInvalidDate = true;
                log.info("executor에서 invalid_date 감지 for entity: {}", entity);
            }

            // 유효한 결과가 있는지 확인
            if ("success".equals(execution.getQueryResultStatus())) {
                hasValidResults = true;
            }

            // 데이터가 있는지 확인
            if (execution.getNoData() == null || !execution.getNoData()) {
                hasNoData = false;
            }

            // 쿼리 에러가 있는지 확인
            if (execution.getQueryError() != null && execution.getQueryError()) {
                hasQueryError = true;
            }

            // 최대 safeCount 확인
            if (execution.getSafeCount() != null && execution.getSafeCount() > maxSafeCount) {
                maxSafeCount = execution.getSafeCount();
            }
        }

        // Invalid date가 있으면 즉시 종료
        if (hasInvalidDate) {
            log.info("SemanticQuery executor에서 invalid_date 감지 - 워크플로우 종료");
            return;
        }

        // No data 처리
        if (hasNoData) {
            log.info("SemanticQuery: 모든 entity에서 데이터 없음");
            try {
                getExecutionContext().executeNode("nodataNode", state);
            } catch (Exception e) {
                log.warn("nodataNode 실행 실패, 기본 메시지 설정: {}", e.getMessage());
                state.setFinalAnswer("요청하신 조건에 해당하는 데이터가 없습니다.");
            }
            return;
        }

        // Query error + safe count 처리
        if (hasQueryError && maxSafeCount < 2) {
            log.info("SemanticQuery: 쿼리 에러 감지, safeguard 실행");
            try {
                getExecutionContext().executeNode("safeguardNode", state);

                // safeguard 후 쿼리 변경 확인
                boolean queryChanged = false;
                for (SemanticQueryWorkflowState.SemanticQueryExecution execution : executionMap.values()) {
                    if (execution.getQueryChanged() != null && execution.getQueryChanged()) {
                        queryChanged = true;
                        break;
                    }
                }

                if (queryChanged) {
                    // 쿼리가 변경된 경우 DSL부터 다시 실행
                    getExecutionContext().executeNode("dsl2SqlNode", state);
                    getExecutionContext().executeNode("runSqlNode", state);

                    // 재실행 후 다시 상태 확인
                    boolean hasInvalidDateAfterRetry = false;
                    boolean hasNoDataAfterRetry = true;

                    for (SemanticQueryWorkflowState.SemanticQueryExecution execution : executionMap.values()) {
                        if (execution.getInvalidDate() != null && execution.getInvalidDate()) {
                            hasInvalidDateAfterRetry = true;
                        }
                        if (execution.getNoData() == null || !execution.getNoData()) {
                            hasNoDataAfterRetry = false;
                        }
                    }

                    if (hasInvalidDateAfterRetry) {
                        log.info("SemanticQuery safeguard 후 invalid_date 감지 - 워크플로우 종료");
                        return;
                    }

                    if (hasNoDataAfterRetry) {
                        getExecutionContext().executeNode("nodataNode", state);
                        return;
                    }

                    // 재실행 후 PostProcess도 다시 실행
                    boolean hasValidResultsAfterRetry = false;
                    for (SemanticQueryWorkflowState.SemanticQueryExecution execution : executionMap.values()) {
                        if ("success".equals(execution.getQueryResultStatus())) {
                            hasValidResultsAfterRetry = true;
                            break;
                        }
                    }

                    if (hasValidResultsAfterRetry) {
                        getExecutionContext().executeNode("postProcessNode", state);
                        hasValidResults = true; // 최종 응답 생성을 위해 플래그 업데이트
                    }
                }
            } catch (Exception e) {
                log.warn("safeguardNode 실행 실패: {}", e.getMessage());
            }
        }

        // 성공적인 결과가 있는 경우 최종 응답 생성
        if (hasValidResults) {
            log.info("SemanticQuery: 유효한 결과 있음, respondent 실행");
            try {
                getExecutionContext().executeNode("semanticQueryRespondentNode", state);
            } catch (Exception e) {
                log.error("semanticQueryRespondentNode 실행 실패: {}", e.getMessage());
                state.setFinalAnswer("결과를 생성하는 중 오류가 발생했습니다.");
            }
        } else {
            log.warn("SemanticQuery: 성공적인 결과가 없음");
            state.setFinalAnswer("요청을 처리하는 중 문제가 발생했습니다.");
        }
    }
}