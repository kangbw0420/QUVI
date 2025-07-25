package com.daquv.agent.workflow.killjoy;

import com.daquv.agent.quvi.dto.QuviRequestDto;
import com.daquv.agent.quvi.workflow.WorkflowExecutionService;;
import com.daquv.agent.workflow.dto.UserInfo;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;

@Service("joyWorkflowExecutionService")
@Slf4j
public class JoyWorkflowExecutionService implements WorkflowExecutionService {

    @Autowired
    private KilljoyWorkflowExecutionContext killjoyWorkflowExecutionContext;

    private final ConcurrentHashMap<String, String> userQuestions = new ConcurrentHashMap<>();

    private final ConcurrentHashMap<String, String> workflowResults = new ConcurrentHashMap<>();


    @Override
    public String getWorkflowType() {
        return "JOY";
    }

    @Override
    public Object createAndInitializeState(QuviRequestDto request, String sessionId, String workflowId) {
        log.info("🎉 JOY 워크플로우 State 생성 및 초기화 시작");

        userQuestions.put(workflowId, request.getUserQuestion());

        log.info("🎉 JOY 워크플로우 State 초기화 완료");
        return request;
    }

    @Override
    public void executeWorkflow(String workflowId) {
        log.info("🎉 JOY 워크플로우 실행 시작 - workflowId: {}", workflowId);

        String userQuestion = userQuestions.get(workflowId);
        if (userQuestion == null) {
            throw new IllegalStateException("사용자 질문을 찾을 수 없습니다: " + workflowId);
        }

        String finalAnswer = killjoyWorkflowExecutionContext.executeKilljoyWorkflow(workflowId, userQuestion);

        // 결과를 임시 저장
        workflowResults.put(workflowId, finalAnswer);

        log.info("🎉 JOY 워크플로우 실행 완료 - workflowId: {}", workflowId);
    }

    @Override
    public Object getFinalState(String workflowId) {
        // 상태 객체 대신 결과 문자열 반환
        return workflowResults.get(workflowId);
    }

    @Override
    public void cleanupState(String workflowId) {
        try {
            workflowResults.remove(workflowId);
            log.debug("JOY 결과 정리 완료 - workflowId: {}", workflowId);
        } catch (Exception e) {
            log.warn("JOY 결과 정리 실패 - workflowId: {}: {}", workflowId, e.getMessage());
        }
    }

    @Override
    public String extractFinalAnswer(String workflowId) {
        try {
            String result = workflowResults.get(workflowId);
            if (result != null) {
                return result;
            }
            return "JOY 처리 중 오류가 발생했습니다.";
        } catch (Exception e) {
            log.error("JOY 최종 답변 추출 실패 - workflowId: {}", workflowId, e);
            return "JOY 처리 중 오류가 발생했습니다.";
        }
    }

    @Override
    public List<?> extractQueryResult(String workflowId) {
        // JOY는 쿼리 결과가 없음
        return new ArrayList<>();
    }

    @Override
    public String extractStartDate(String workflowId) {
        // JOY는 날짜 정보가 없음
        return null;
    }

    @Override
    public String extractEndDate(String workflowId) {
        // JOY는 날짜 정보가 없음
        return null;
    }

    @Override
    public String extractSqlQuery(String workflowId) {
        // JOY는 SQL 쿼리가 없음
        return null;
    }

    @Override
    public String extractSelectedTable(String workflowId) {
        // JOY는 테이블 선택이 없음
        return null;
    }

    @Override
    public Boolean extractHasNext(String workflowId) {
        // JOY는 페이징이 없음
        return false;
    }

    @Override
    public UserInfo extractUserInfo(String workflowId) {
        log.debug("JOY 워크플로우는 UserInfo를 제공하지 않습니다.");
        return null;
    }
}
