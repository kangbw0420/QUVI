package com.daquv.agent.quvi.llmadmin;

import com.daquv.agent.quvi.entity.Workflow;
import com.daquv.agent.quvi.entity.Session;
import com.daquv.agent.quvi.repository.WorkflowRepository;
import com.daquv.agent.quvi.repository.SessionRepository;
import com.daquv.agent.quvi.util.DatabaseProfilerAspect;
import com.daquv.agent.quvi.util.RequestProfiler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class WorkflowService {

    @Autowired
    private RequestProfiler requestProfiler;

    private static final Logger log = LoggerFactory.getLogger(WorkflowService.class);
    private final WorkflowRepository workflowRepository;
    private final SessionRepository sessionRepository;

    public WorkflowService(WorkflowRepository workflowRepository, SessionRepository sessionRepository) {
        this.workflowRepository = workflowRepository;
        this.sessionRepository = sessionRepository;
    }

    /**
     * 새로운 체인을 생성하고 초기 상태를 기록
     *
     * @param sessionId 대화 ID
     * @param userQuestion 사용자 질문
     * @return 생성된 chain ID
     */
    @Transactional
    public String createWorkflow(String sessionId, String userQuestion) {
        log.info("createWorkflow start - sessionId: {}, userQuestion: {}", sessionId, userQuestion);
        String workflowId = UUID.randomUUID().toString();

        DatabaseProfilerAspect.setWorkflowId(workflowId);
        log.debug("ChainService에서 chainId 설정: {}", workflowId);

        try {
            // Session 조회
            Session session = sessionRepository.findBySessionId(sessionId)
                    .orElseThrow(() -> new IllegalArgumentException("Session not found: " + sessionId));

            // Workflow 생성
            Workflow workflow = Workflow.create(workflowId, session, userQuestion, Workflow.WorkflowStatus.active);
            workflowRepository.save(workflow);

            log.info("createWorkflow end - chainId: {}", workflowId);
            return workflowId;

        } catch (Exception e) {
            log.error("Error in createWorkflow - sessionId: {}, userQuestion: {}", sessionId, userQuestion, e);
            throw new RuntimeException("Failed to create workflow", e);
        }
    }

    /**
     * 체인 완료 시 답변과 종료 시간을 기록
     *
     * @param chainId 체인 ID
     * @param finalAnswer 최종 답변
     * @return 성공 여부
     */
    @Transactional
    public boolean completeWorkflow(String chainId, String finalAnswer) {
        log.info("completeWorkflow start - chainId: {}, finalAnswer: {}", chainId, finalAnswer);

        long startTime = System.currentTimeMillis();
        try {
            Workflow workflow = workflowRepository.findById(chainId)
                    .orElseThrow(() -> new IllegalArgumentException("Chain not found: " + chainId));

            workflow.completeChain(finalAnswer);
            workflowRepository.save(workflow);

            log.info("completeWorkflow end - chainId: {}", chainId);
            return true;

        } catch (Exception e) {
            log.error("Error in completeWorkflow - chainId: {}, finalAnswer: {}", chainId, finalAnswer, e);
            throw new RuntimeException("Failed to complete workflow", e);
        }
    }

    /**
     * 체인 실행 중 오류 발생 시 상태를 error로 변경
     *
     * @param chainId 체인 ID
     * @param errorMessage 오류 메시지
     * @return 성공 여부
     */
    @Transactional
    public void markChainError(String chainId, String errorMessage, String errorLog) {
        long startTime = System.currentTimeMillis();
        try {
            Workflow workflow = workflowRepository.findById(chainId)
                    .orElseThrow(() -> new RuntimeException("Chain not found: " + chainId));

            workflow.markError(errorMessage, errorLog);
            workflowRepository.saveAndFlush(workflow); // 즉시 DB에 반영

            log.info("✅ 체인 에러 상태 저장 완료 - chainId: {}", chainId);
        } catch (Exception e) {
            log.error("❌ 체인 에러 상태 저장 실패 - chainId: {}, error: {}", chainId, e.getMessage(), e);
            throw new RuntimeException("Failed to save chain error", e);
        }
    }

    /**
     * 체인 로그 업데이트
     */
    @Transactional
    public void updateChainLog(String chainId, String chainLogText) {
        long startTime = System.currentTimeMillis();
        try {
            Workflow workflow = workflowRepository.findById(chainId)
                    .orElseThrow(() -> new RuntimeException("Chain not found: " + chainId));

            workflowRepository.saveAndFlush(workflow); // 즉시 DB에 반영

            log.info("✅ 체인 로그 업데이트 완료 - chainId: {}", chainId);
        } catch (Exception e) {
            log.error("❌ 체인 로그 업데이트 실패 - chainId: {}, error: {}", chainId, e.getMessage(), e);
            throw new RuntimeException("Failed to update chain log", e);
        }
    }
}
