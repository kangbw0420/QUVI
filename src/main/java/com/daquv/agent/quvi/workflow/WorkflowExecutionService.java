package com.daquv.agent.quvi.workflow;

import com.daquv.agent.quvi.dto.QuviRequestDto;
import com.daquv.agent.workflow.dto.UserInfo;

import java.util.List;

public interface WorkflowExecutionService {
    Object createAndInitializeState(QuviRequestDto request, String sessionId, String workflowId);
    void executeWorkflow(String workflowId);
    Object getFinalState(String workflowId);
    void cleanupState(String workflowId);
    String getWorkflowType();

    /**
     * HIL 이후 워크플로우 재개
     */
    default void resumeWorkflowAfterHil(String workflowId, String userInput) {
        throw new UnsupportedOperationException(
                getWorkflowType() + " 워크플로우는 HIL 재개를 지원하지 않습니다.");
    }

    /**
     * State 객체에서 최종 답변 추출
     */
    String extractFinalAnswer(String workflowId);

    /**
     * State 객체에서 쿼리 결과 추출
     */
    List<?> extractQueryResult(String workflowId);

    /**
     * State 객체에서 시작 날짜 추출
     */
    String extractStartDate(String workflowId);

    /**
     * State 객체에서 종료 날짜 추출
     */
    String extractEndDate(String workflowId);

    /**
     * State 객체에서 SQL 쿼리 추출
     */
    String extractSqlQuery(String workflowId);

    /**
     * State 객체에서 선택된 테이블/API 추출
     */
    String extractSelectedTable(String workflowId);

    /**
     * State 객체에서 hasNext 플래그 추출
     */
    Boolean extractHasNext(String workflowId);

    /**
     * State 객체에서 UserInfo 추출
     */
    UserInfo extractUserInfo(String workflowId);
}

