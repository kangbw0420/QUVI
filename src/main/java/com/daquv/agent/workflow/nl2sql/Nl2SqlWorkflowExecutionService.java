package com.daquv.agent.workflow.nl2sql;

import com.daquv.agent.quvi.dto.QuviRequestDto;
import com.daquv.agent.quvi.workflow.WorkflowExecutionService;
import com.daquv.agent.workflow.dto.UserInfo;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service("nl2SqlWorkflowExecutionService")
@Slf4j
public class Nl2SqlWorkflowExecutionService implements WorkflowExecutionService {
    @Autowired
    private Nl2SqlStateManager stateManager;

    @Autowired
    private Nl2SqlWorkflowExecutionContext nl2sqlWorkflowContext;

    @Override
    public String getWorkflowType() {
        return "NL2SQL";
    }

    @Override
    public Object createAndInitializeState(QuviRequestDto request, String sessionId, String workflowId) {
        log.info("💾 NL2SQL 워크플로우 State 생성 및 초기화 시작");

        Nl2SqlWorkflowState state = stateManager.createState(workflowId);
        initializeNl2SqlState(state, request, workflowId);

        log.info("💾 NL2SQL 워크플로우 State 초기화 완료");
        return state;
    }

    @Override
    public void executeWorkflow(String workflowId) {
        log.info("💾 NL2SQL 워크플로우 실행 시작 - workflowId: {}", workflowId);
        nl2sqlWorkflowContext.executeNl2SqlWorkflow(workflowId);
        log.info("💾 NL2SQL 워크플로우 실행 완료 - workflowId: {}", workflowId);
    }

    @Override
    public Object getFinalState(String workflowId) {
        return stateManager.getState(workflowId);
    }

    @Override
    public void cleanupState(String workflowId) {
        try {
            stateManager.removeState(workflowId);
            log.debug("NL2SQL State 정리 완료 - workflowId: {}", workflowId);
        } catch (Exception e) {
            log.warn("NL2SQL State 정리 실패 - workflowId: {}: {}", workflowId, e.getMessage());
        }
    }

    @Override
    public String extractFinalAnswer(String workflowId) {
        try {
            Nl2SqlWorkflowState state = stateManager.getState(workflowId);
            if (state != null && state.getFinalAnswer() != null) {
                return state.getFinalAnswer();
            }
            return "NL2SQL 처리 중 오류가 발생했습니다.";
        } catch (Exception e) {
            log.error("NL2SQL 최종 답변 추출 실패 - workflowId: {}", workflowId, e);
            return "NL2SQL 처리 중 오류가 발생했습니다.";
        }
    }

    @Override
    public List<?> extractQueryResult(String workflowId) {
        try {
            Nl2SqlWorkflowState state = stateManager.getState(workflowId);
            if (state != null && state.getQueryResult() != null) {
                return state.getQueryResult();
            }
            return new ArrayList<>();
        } catch (Exception e) {
            log.error("NL2SQL 쿼리 결과 추출 실패 - workflowId: {}", workflowId, e);
            return new ArrayList<>();
        }
    }

    @Override
    public String extractStartDate(String workflowId) {
        try {
            Nl2SqlWorkflowState state = stateManager.getState(workflowId);
            if (state != null) {
                return state.getStartDate();
            }
            return null;
        } catch (Exception e) {
            log.error("NL2SQL 시작 날짜 추출 실패 - workflowId: {}", workflowId, e);
            return null;
        }
    }

    @Override
    public String extractEndDate(String workflowId) {
        try {
            Nl2SqlWorkflowState state = stateManager.getState(workflowId);
            if (state != null) {
                return state.getEndDate();
            }
            return null;
        } catch (Exception e) {
            log.error("NL2SQL 종료 날짜 추출 실패 - workflowId: {}", workflowId, e);
            return null;
        }
    }

    @Override
    public String extractSqlQuery(String workflowId) {
        try {
            Nl2SqlWorkflowState state = stateManager.getState(workflowId);
            if (state != null) {
                return state.getSqlQuery();
            }
            return null;
        } catch (Exception e) {
            log.error("NL2SQL SQL 쿼리 추출 실패 - workflowId: {}", workflowId, e);
            return null;
        }
    }

    @Override
    public String extractSelectedTable(String workflowId) {
        try {
            Nl2SqlWorkflowState state = stateManager.getState(workflowId);
            if (state != null) {
                return state.getSelectedTable();
            }
            return null;
        } catch (Exception e) {
            log.error("NL2SQL 선택된 테이블 추출 실패 - workflowId: {}", workflowId, e);
            return null;
        }
    }

    @Override
    public Boolean extractHasNext(String workflowId) {
        try {
            Nl2SqlWorkflowState state = stateManager.getState(workflowId);
            if (state != null) {
                return state.getHasNext();
            }
            return false;
        } catch (Exception e) {
            log.error("NL2SQL hasNext 플래그 추출 실패 - workflowId: {}", workflowId, e);
            return false;
        }
    }

    @Override
    public UserInfo extractUserInfo(String workflowId) {
        try {
            Nl2SqlWorkflowState state = stateManager.getState(workflowId);
            if (state != null) {
                return state.getUserInfo();
            }
            return null;
        } catch (Exception e) {
            log.error("NL2SQL UserInfo 추출 실패 - workflowId: {}", workflowId, e);
            return null;
        }
    }

    /**
     * NL2SQL 워크플로우 State 초기화
     */
    private void initializeNl2SqlState(Nl2SqlWorkflowState state, QuviRequestDto request, String workflowId) {
        state.setUserQuestion(request.getUserQuestion());
        state.setUserInfo(UserInfo.builder()
                .userId(request.getUserId())
                .companyId(request.getCompanyId())
                .useInttId(request.getUseInttId())
                .build());
        state.setWorkflowId(workflowId);

        log.info("💾 NL2SQL 워크플로우용 상태 초기화 완료");
    }

    /**
     * HIL 이후 NL2SQL 워크플로우 재개 (인터페이스 메서드 오버라이드)
     */
    @Override
    public void resumeWorkflowAfterHil(String workflowId, String userInput) {
        log.info("💾 NL2SQL HIL 워크플로우 재개 실행 - workflowId: {}, userInput: {}",
                workflowId, userInput);
        nl2sqlWorkflowContext.resumeNl2SqlWorkflowAfterDateClarification(workflowId, userInput);
        log.info("💾 NL2SQL HIL 워크플로우 재개 완료 - workflowId: {}", workflowId);
    }
}