package com.daquv.agent.workflow.semanticquery;

import com.daquv.agent.quvi.dto.QuviRequestDto;
import com.daquv.agent.quvi.workflow.WorkflowExecutionService;
import com.daquv.agent.workflow.dto.UserInfo;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service("semanticQueryWorkflowExecutionService") // Bean 이름도 변경
@Slf4j
public class SemanticQueryWorkflowExecutionService implements WorkflowExecutionService {

    @Autowired
    private SemanticQueryStateManager stateManager;

    @Autowired
    private SemanticQueryWorkflowExecutionContext semanticQueryWorkflowContext;

    @Override
    public String getWorkflowType() {
        return "SEMANTICQUERY";
    }

    @Override
    public Object createAndInitializeState(QuviRequestDto request, String sessionId, String workflowId) {
        log.info("💾 SEMANTICQUERY 워크플로우 State 생성 및 초기화 시작");

        SemanticQueryWorkflowState state = stateManager.createState(workflowId);
        initializeSemanticQueryState(state, request, workflowId);

        log.info("💾 SEMANTICQUERY 워크플로우 State 초기화 완료");
        return state;
    }

    @Override
    public void executeWorkflow(String workflowId) {
        log.info("💾 SEMANTICQUERY 워크플로우 실행 시작 - workflowId: {}", workflowId);
        semanticQueryWorkflowContext.executeSemanticQueryWorkflow(workflowId);
        log.info("💾 SEMANTICQUERY 워크플로우 실행 완료 - workflowId: {}", workflowId);
    }

    @Override
    public Object getFinalState(String workflowId) {
        return stateManager.getState(workflowId);
    }

    @Override
    public void cleanupState(String workflowId) {
        try {
            stateManager.removeState(workflowId);
            log.debug("SEMANTICQUERY State 정리 완료 - workflowId: {}", workflowId);
        } catch (Exception e) {
            log.warn("SEMANTICQUERY State 정리 실패 - workflowId: {}: {}", workflowId, e.getMessage());
        }
    }

    @Override
    public String extractFinalAnswer(String workflowId) {
        try {
            SemanticQueryWorkflowState state = stateManager.getState(workflowId);
            if (state != null && state.getFinalAnswer() != null) {
                return state.getFinalAnswer();
            }
            return "SEMANTICQUERY 처리 중 오류가 발생했습니다.";
        } catch (Exception e) {
            log.error("SEMANTICQUERY 최종 답변 추출 실패 - workflowId: {}", workflowId, e);
            return "SEMANTICQUERY 처리 중 오류가 발생했습니다.";
        }
    }

    @Override
    public List<?> extractQueryResult(String workflowId) {
        try {
            SemanticQueryWorkflowState state = stateManager.getState(workflowId);
            if (state != null && state.getSemanticQueryExecutionMap() != null) {
                // SemanticQuery는 복수의 execution이 있을 수 있으므로 모든 결과를 합쳐서 반환
                List<Object> allResults = new ArrayList<>();
                for (SemanticQueryWorkflowState.SemanticQueryExecution execution :
                        state.getSemanticQueryExecutionMap().values()) {
                    if (execution.getQueryResult() != null) {
                        allResults.addAll(execution.getQueryResult().values());
                    }
                }
                return allResults;
            }
            return new ArrayList<>();
        } catch (Exception e) {
            log.error("SEMANTICQUERY 쿼리 결과 추출 실패 - workflowId: {}", workflowId, e);
            return new ArrayList<>();
        }
    }

    @Override
    public String extractStartDate(String workflowId) {
        try {
            SemanticQueryWorkflowState state = stateManager.getState(workflowId);
            if (state != null) {
                return state.getStartDate();
            }
            return null;
        } catch (Exception e) {
            log.error("SEMANTICQUERY 시작 날짜 추출 실패 - workflowId: {}", workflowId, e);
            return null;
        }
    }

    @Override
    public String extractEndDate(String workflowId) {
        try {
            SemanticQueryWorkflowState state = stateManager.getState(workflowId);
            if (state != null) {
                return state.getEndDate();
            }
            return null;
        } catch (Exception e) {
            log.error("SEMANTICQUERY 종료 날짜 추출 실패 - workflowId: {}", workflowId, e);
            return null;
        }
    }

    @Override
    public String extractSqlQuery(String workflowId) {
        try {
            SemanticQueryWorkflowState state = stateManager.getState(workflowId);
            if (state != null && state.getSemanticQueryExecutionMap() != null) {
                // 첫 번째 execution의 첫 번째 SQL 쿼리를 반환 (기존 로직과 호환성 유지)
                for (SemanticQueryWorkflowState.SemanticQueryExecution execution :
                        state.getSemanticQueryExecutionMap().values()) {
                    if (execution.getSqlQuery() != null && !execution.getSqlQuery().isEmpty()) {
                        return execution.getSqlQuery().values().iterator().next();
                    }
                }
            }
            return null;
        } catch (Exception e) {
            log.error("SEMANTICQUERY SQL 쿼리 추출 실패 - workflowId: {}", workflowId, e);
            return null;
        }
    }

    @Override
    public String extractSelectedTable(String workflowId) {
        try {
            SemanticQueryWorkflowState state = stateManager.getState(workflowId);
            if (state != null) {
                return state.getSelectedTable();
            }
            return null;
        } catch (Exception e) {
            log.error("SEMANTICQUERY 선택된 테이블 추출 실패 - workflowId: {}", workflowId, e);
            return null;
        }
    }

    @Override
    public Boolean extractHasNext(String workflowId) {
        try {
            SemanticQueryWorkflowState state = stateManager.getState(workflowId);
            if (state != null && state.getSemanticQueryExecutionMap() != null) {
                // 하나라도 hasNext가 true인 execution이 있으면 true 반환
                for (SemanticQueryWorkflowState.SemanticQueryExecution execution :
                        state.getSemanticQueryExecutionMap().values()) {
                    if (execution.getHasNext() != null && execution.getHasNext()) {
                        return true;
                    }
                }
            }
            return false;
        } catch (Exception e) {
            log.error("SEMANTICQUERY hasNext 플래그 추출 실패 - workflowId: {}", workflowId, e);
            return false;
        }
    }

    /**
     * SEMANTICQUERY 워크플로우 State 초기화
     */
    private void initializeSemanticQueryState(SemanticQueryWorkflowState state, QuviRequestDto request, String workflowId) {
        state.setUserQuestion(request.getUserQuestion());
        state.setUserInfo(UserInfo.builder()
                .userId(request.getUserId())
                .companyId(request.getCompanyId())
                .useInttId(request.getUseInttId())
                .build());
        state.setWorkflowId(workflowId);
        state.setNodeId("node_" + System.currentTimeMillis());

        log.info("💾 SEMANTICQUERY 워크플로우용 상태 초기화 완료");
    }

    /**
     * HIL 이후 SemanticQuery 워크플로우 재개 (인터페이스 메서드 오버라이드)
     */
    @Override
    public void resumeWorkflowAfterHil(String workflowId, String userInput) {
        log.info("💾 SemanticQuery HIL 워크플로우 재개 실행 - workflowId: {}, userInput: {}",
                workflowId, userInput);
        semanticQueryWorkflowContext.resumeSemanticQueryWorkflowAfterDateClarification(workflowId, userInput);
        log.info("💾 SemanticQuery HIL 워크플로우 재개 완료 - workflowId: {}", workflowId);
    }
}