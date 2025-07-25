package com.daquv.agent.workflow.killjoy;

import com.daquv.agent.quvi.dto.QuviRequestDto;
import com.daquv.agent.quvi.workflow.WorkflowExecutionService;
import com.daquv.agent.workflow.ChainStateManager;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.workflow.dto.UserInfo;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service("joyWorkflowExecutionService") // Bean 이름도 변경
@Slf4j
public class JoyWorkflowExecutionService implements WorkflowExecutionService {

    @Autowired
    private ChainStateManager stateManager;

    @Autowired
    private KilljoyWorkflowExecutionContext killjoyWorkflowExecutionContext;

    @Override
    public String getWorkflowType() {
        return "JOY";
    }

    @Override
    public Object createAndInitializeState(QuviRequestDto request, String sessionId, String workflowId) {
        log.info("🎉 JOY 워크플로우 State 생성 및 초기화 시작");

        WorkflowState state = stateManager.createState(workflowId);
        initializeJoyState(state, request, sessionId, workflowId);

        log.info("🎉 JOY 워크플로우 State 초기화 완료");
        return state;
    }

    @Override
    public void executeWorkflow(String workflowId) {
        log.info("🎉 JOY 워크플로우 실행 시작 - workflowId: {}", workflowId);
        killjoyWorkflowExecutionContext.executeKilljoyWorkflow(workflowId);
        log.info("🎉 JOY 워크플로우 실행 완료 - workflowId: {}", workflowId);
    }

    @Override
    public Object getFinalState(String workflowId) {
        return stateManager.getState(workflowId);
    }

    @Override
    public void cleanupState(String workflowId) {
        try {
            stateManager.removeState(workflowId);
            log.debug("JOY State 정리 완료 - workflowId: {}", workflowId);
        } catch (Exception e) {
            log.warn("JOY State 정리 실패 - workflowId: {}: {}", workflowId, e.getMessage());
        }
    }

    @Override
    public String extractFinalAnswer(String workflowId) {
        try {
            WorkflowState state = stateManager.getState(workflowId);
            if (state != null && state.getFinalAnswer() != null) {
                return state.getFinalAnswer();
            }
            return "JOY 처리 중 오류가 발생했습니다.";
        } catch (Exception e) {
            log.error("JOY 최종 답변 추출 실패 - workflowId: {}", workflowId, e);
            return "JOY 처리 중 오류가 발생했습니다.";
        }
    }

    @Override
    public List<?> extractQueryResult(String workflowId) {
        try {
            WorkflowState state = stateManager.getState(workflowId);
            if (state != null && state.getQueryResult() != null) {
                return state.getQueryResult();
            }
            return new ArrayList<>();
        } catch (Exception e) {
            log.error("JOY 쿼리 결과 추출 실패 - workflowId: {}", workflowId, e);
            return new ArrayList<>();
        }
    }

    @Override
    public String extractStartDate(String workflowId) {
        try {
            WorkflowState state = stateManager.getState(workflowId);
            if (state != null) {
                return state.getStartDate();
            }
            return null;
        } catch (Exception e) {
            log.error("JOY 시작 날짜 추출 실패 - workflowId: {}", workflowId, e);
            return null;
        }
    }

    @Override
    public String extractEndDate(String workflowId) {
        try {
            WorkflowState state = stateManager.getState(workflowId);
            if (state != null) {
                return state.getEndDate();
            }
            return null;
        } catch (Exception e) {
            log.error("JOY 종료 날짜 추출 실패 - workflowId: {}", workflowId, e);
            return null;
        }
    }

    @Override
    public String extractSqlQuery(String workflowId) {
        try {
            WorkflowState state = stateManager.getState(workflowId);
            if (state != null) {
                return state.getSqlQuery();
            }
            return null;
        } catch (Exception e) {
            log.error("JOY SQL 쿼리 추출 실패 - workflowId: {}", workflowId, e);
            return null;
        }
    }

    @Override
    public String extractSelectedTable(String workflowId) {
        try {
            WorkflowState state = stateManager.getState(workflowId);
            if (state != null) {
                return state.getSelectedTable();
            }
            return null;
        } catch (Exception e) {
            log.error("JOY 선택된 테이블 추출 실패 - workflowId: {}", workflowId, e);
            return null;
        }
    }

    @Override
    public Boolean extractHasNext(String workflowId) {
        try {
            WorkflowState state = stateManager.getState(workflowId);
            if (state != null && state.getHasNext() != null) {
                return state.getHasNext();
            }
            return false;
        } catch (Exception e) {
            log.error("JOY hasNext 플래그 추출 실패 - workflowId: {}", workflowId, e);
            return false;
        }
    }

    /**
     * JOY 워크플로우 State 초기화
     */
    private void initializeJoyState(WorkflowState state, QuviRequestDto request, String sessionId, String workflowId) {
        state.setUserQuestion(request.getUserQuestion());
        state.setUserInfo(UserInfo.builder()
                .userId(request.getUserId())
                .companyId(request.getCompanyId())
                .useInttId(request.getUseInttId())
                .build());
        state.setWorkflowId(workflowId);
        state.setNodeId("node_" + System.currentTimeMillis());
        state.setSelectedWorkflow("JOY");
        state.setIsJoy(true);

        log.info("🎉 JOY 워크플로우용 상태 초기화 완료");
    }
}
