package com.daquv.agent.workflow.tooluse;

import com.daquv.agent.quvi.dto.QuviRequestDto;
import com.daquv.agent.quvi.workflow.WorkflowExecutionService;
import com.daquv.agent.workflow.dto.UserInfo;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service("toolUseWorkflowExecutionService") // Bean 이름도 변경
@Slf4j
public class ToolUseWorkflowExecutionService implements WorkflowExecutionService {

    @Autowired
    private ToolUseStateManager stateManager;

    @Autowired
    private ToolUseWorkflowExecutionContext toolUseWorkflowContext;

    @Override
    public String getWorkflowType() {
        return "TOOLUSE";
    }

    @Override
    public Object createAndInitializeState(QuviRequestDto request, String sessionId, String workflowId) {
        log.info("🔌 TOOLUSE 워크플로우 State 생성 및 초기화 시작");

        ToolUseWorkflowState state = stateManager.createState(workflowId);
        initializeToolUseState(state, request, sessionId, workflowId);

        log.info("🔌 TOOLUSE 워크플로우 State 초기화 완료");
        return state;
    }

    @Override
    public void executeWorkflow(String workflowId) {
        log.info("🔌 TOOLUSE 워크플로우 실행 시작 - workflowId: {}", workflowId);
        toolUseWorkflowContext.executeToolUseWorkflow(workflowId);
        log.info("🔌 TOOLUSE 워크플로우 실행 완료 - workflowId: {}", workflowId);
    }

    @Override
    public Object getFinalState(String workflowId) {
        return stateManager.getState(workflowId);
    }

    @Override
    public void cleanupState(String workflowId) {
        try {
            stateManager.removeState(workflowId);
            log.debug("TOOLUSE State 정리 완료 - workflowId: {}", workflowId);
        } catch (Exception e) {
            log.warn("TOOLUSE State 정리 실패 - workflowId: {}: {}", workflowId, e.getMessage());
        }
    }

    @Override
    public String extractFinalAnswer(String workflowId) {
        try {
            ToolUseWorkflowState state = stateManager.getState(workflowId);
            if (state != null && state.getFinalAnswer() != null) {
                return state.getFinalAnswer();
            }
            return "TOOLUSE 처리 중 오류가 발생했습니다.";
        } catch (Exception e) {
            log.error("TOOLUSE 최종 답변 추출 실패 - workflowId: {}", workflowId, e);
            return "TOOLUSE 처리 중 오류가 발생했습니다.";
        }
    }

    @Override
    public List<?> extractQueryResult(String workflowId) {
        try {
            ToolUseWorkflowState state = stateManager.getState(workflowId);
            if (state != null && state.getQueryResult() != null) {
                return state.getQueryResult();
            }
            return new ArrayList<>();
        } catch (Exception e) {
            log.error("TOOLUSE 쿼리 결과 추출 실패 - workflowId: {}", workflowId, e);
            return new ArrayList<>();
        }
    }

    @Override
    public String extractStartDate(String workflowId) {
        try {
            ToolUseWorkflowState state = stateManager.getState(workflowId);
            if (state != null) {
                return state.getStartDate();
            }
            return null;
        } catch (Exception e) {
            log.error("TOOLUSE 시작 날짜 추출 실패 - workflowId: {}", workflowId, e);
            return null;
        }
    }

    @Override
    public String extractEndDate(String workflowId) {
        try {
            ToolUseWorkflowState state = stateManager.getState(workflowId);
            if (state != null) {
                return state.getEndDate();
            }
            return null;
        } catch (Exception e) {
            log.error("TOOLUSE 종료 날짜 추출 실패 - workflowId: {}", workflowId, e);
            return null;
        }
    }

    @Override
    public String extractSqlQuery(String workflowId) {
        try {
            ToolUseWorkflowState state = stateManager.getState(workflowId);
            if (state != null) {
                return state.getSqlQuery();
            }
            return null;
        } catch (Exception e) {
            log.error("TOOLUSE SQL 쿼리 추출 실패 - workflowId: {}", workflowId, e);
            return null;
        }
    }

    @Override
    public String extractSelectedTable(String workflowId) {
        try {
            ToolUseWorkflowState state = stateManager.getState(workflowId);
            if (state != null) {
                return state.getSelectedApi(); // API명을 selected_table로 반환
            }
            return null;
        } catch (Exception e) {
            log.error("TOOLUSE 선택된 API 추출 실패 - workflowId: {}", workflowId, e);
            return null;
        }
    }

    @Override
    public Boolean extractHasNext(String workflowId) {
        try {
            ToolUseWorkflowState state = stateManager.getState(workflowId);
            if (state != null && state.getHasNext() != null) {
                return state.getHasNext();
            }
            return false;
        } catch (Exception e) {
            log.error("TOOLUSE hasNext 플래그 추출 실패 - workflowId: {}", workflowId, e);
            return false;
        }
    }

    @Override
    public UserInfo extractUserInfo(String workflowId) {
        try {
            ToolUseWorkflowState state = stateManager.getState(workflowId);
            if (state != null) {
                return state.getUserInfo();
            }
            return null;
        } catch (Exception e) {
            log.error("TOOLUSE UserInfo 추출 실패 - workflowId: {}", workflowId, e);
            return null;
        }
    }

    /**
     * TOOLUSE 워크플로우 State 초기화
     */
    private void initializeToolUseState(ToolUseWorkflowState state, QuviRequestDto request, String sessionId, String workflowId) {
        state.setUserQuestion(request.getUserQuestion());
        state.setUserInfo(UserInfo.builder()
                .userId(request.getUserId())
                .companyId(request.getCompanyId())
                .useInttId(request.getUseInttId())
                .build());
        state.setWorkflowId(workflowId);
        state.setNodeId("node_" + System.currentTimeMillis());
        state.setSelectedWorkflow("TOOLUSE");

        // TOOLUSE 특화 초기화
        state.setSafeCount(0);
        state.setQueryResultStatus("");
        state.setSqlError("");
        state.setSqlQuery("");
        state.setQueryResult(new ArrayList<>());
        state.setFinalAnswer("");
        state.setSelectedApi(""); // TOOLUSE는 API 사용
        state.setFString("");

        // 플래그 초기화
        state.setNoData(false);
        state.setFutureDate(false);
        state.setInvalidDate(false);
        state.setQueryError(false);
        state.setQueryChanged(false);
        state.setHasNext(false);

        log.info("🔌 TOOLUSE 워크플로우용 상태 초기화 완료");
    }
}
