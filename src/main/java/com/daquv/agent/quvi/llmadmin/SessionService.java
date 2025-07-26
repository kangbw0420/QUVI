package com.daquv.agent.quvi.llmadmin;

import com.daquv.agent.quvi.dto.QuviRequestDto;
import com.daquv.agent.quvi.entity.Session;
import com.daquv.agent.quvi.repository.SessionRepository;
import com.daquv.agent.quvi.util.DatabaseProfilerAspect;
import com.daquv.agent.quvi.util.RequestProfiler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import javax.servlet.http.HttpServletRequest;
import java.util.Optional;
import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class SessionService {

    private static final Logger log = LoggerFactory.getLogger(SessionService.class);
    private final SessionRepository sessionRepository;

    @Autowired
    private RequestProfiler requestProfiler;

    public SessionService(SessionRepository sessionRepository) {
        this.sessionRepository = sessionRepository;
    }

    /**
     * sessionId가 존재하고 status가 active인지 확인
     */
    public boolean checkSessionId(String sessionId) {
        log.info("checkSessionId start - sessionId: {}", sessionId);

        try {
            return sessionRepository.findBySessionId(sessionId)
                    .map(session -> Session.SessionStatus.active.equals(session.getSessionStatus()))
                    .orElse(false);
        } catch (Exception e) {
            log.error("Error checking sessionId ID: {}", sessionId, e);
            return false;
        }
    }

    /**
     * 새로운 sessionId 생성. UUID로 ID 생성하고 status는 active로 설정
     */
    @Transactional
    public String makeSessionId(QuviRequestDto request) {
        log.info("makeSessionId start - userId: {}", request.getUserId());
        String userId = request.getUserId();
        String companyId = request.getCompanyId();
        log.debug("Retrieved companyId: {} for userId: {}", companyId, userId);

        String workflowId = getCurrentWorkflowId();
        if (workflowId != null) {
            DatabaseProfilerAspect.setWorkflowId(workflowId);
            log.debug("SessionService에서 workflowId 설정: {}", workflowId);
        }

        try {
            String sessionId = UUID.randomUUID().toString();
            Session session = Session.create(userId, sessionId, companyId);
            sessionRepository.save(session);
            log.info("makeSessionId end - sessionId: {}", sessionId);
            return sessionId;
        } catch (Exception e) {
            log.error("Error creating conversation for userId: {}", userId, e);
            throw new RuntimeException("Failed to create conversation", e);
        }
    }

    /**
     * 대화 종료 처리
     */
    @Transactional
    public void endConversation(String sessionId) {
        log.info("endConversation start - sessionId: {}", sessionId);

        try {
            Session session = sessionRepository.findBySessionId(sessionId)
                    .orElseThrow(() -> new IllegalArgumentException("Conversation not found: " + sessionId));
            session.endConversation();
            sessionRepository.save(session);
            log.info("endConversation end - sessionId: {}", sessionId);
        } catch (Exception e) {
            log.error("Error ending conversation: {}", sessionId, e);
            throw new RuntimeException("Failed to end conversation", e);
        }
    }

    /**
     * 대화 상태 업데이트
     */
    @Transactional
    public void updateSessionStatus(String sessionId, Session.SessionStatus status) {
        log.info("updateSessionStatus start - sessionId: {}, status: {}", sessionId, status);

        try {
            Session session = sessionRepository.findBySessionId(sessionId)
                    .orElseThrow(() -> new IllegalArgumentException("Session not found: " + sessionId));
            session.updateStatus(status);
            sessionRepository.save(session);
            log.info("updateSessionStatus end - sessionId: {}", sessionId);
        } catch (Exception e) {
            log.error("Error updating session status: {}", sessionId, e);
            throw new RuntimeException("Failed to update session status", e);
        }
    }

    /**
     * 대화 조회
     */
    public Optional<Session> getSession(String sessionId) {
        log.info("getSession - sessionId: {}", sessionId);
        return sessionRepository.findBySessionId(sessionId);
    }

    /**
     * 세션 ID 확인 또는 새로 생성
     */
    public String getOrCreateSessionId(QuviRequestDto request) {
        String sessionId = request.getSessionId();

        if (sessionId != null && !sessionId.isEmpty() && checkSessionId(sessionId)) {
            log.debug("기존 세션 ID 사용: {}", sessionId);
            return sessionId;
        } else {
            String newSessionId = makeSessionId(request);
            log.debug("새 세션 ID 생성: {}", newSessionId);
            return newSessionId;
        }
    }

    private String getCurrentWorkflowId() {
        try {
            RequestAttributes requestAttributes = RequestContextHolder.getRequestAttributes();
            if (requestAttributes instanceof ServletRequestAttributes) {
                HttpServletRequest request = ((ServletRequestAttributes) requestAttributes).getRequest();

                Object workflowIdIdAttr = request.getAttribute("workflowId");
                if (workflowIdIdAttr != null) {
                    return workflowIdIdAttr.toString();
                }

                Object xWorkflowIdAttr = request.getAttribute("X-Workflow-Id");
                if (xWorkflowIdAttr != null) {
                    return xWorkflowIdAttr.toString();
                }
            }
        } catch (Exception e) {
            log.debug("getCurrentWorkflowId 실패: {}", e.getMessage());
        }
        return null;
    }
}