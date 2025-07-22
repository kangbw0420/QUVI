package com.daquv.agent.quvi.llmadmin;

import com.daquv.agent.quvi.entity.Session;
import com.daquv.agent.quvi.repository.SessionRepository;
import com.daquv.agent.quvi.repository.UsersRepository;
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
    private final UsersRepository usersRepository;

    @Autowired
    private RequestProfiler requestProfiler;

    public SessionService(SessionRepository sessionRepository,
                          UsersRepository usersRepository) {
        this.sessionRepository = sessionRepository;
        this.usersRepository = usersRepository;
    }

    /**
     * conversation_id가 존재하고 status가 active인지 확인
     */
    public boolean checkConversationId(String conversationId) {
        log.info("checkConversationId start - conversationId: {}", conversationId);

        try {
            return sessionRepository.findBySessionId(conversationId)
                    .map(conversation -> Session.SessionStatus.active.equals(conversation.getConversationStatus()))
                    .orElse(false);
        } catch (Exception e) {
            log.error("Error checking conversation ID: {}", conversationId, e);
            return false;
        }
    }

    /**
     * 새로운 conversation 생성. UUID로 ID 생성하고 status는 active로 설정
     */
    @Transactional
    public String makeSessionId(String userId) {
        log.info("makeConversationId start - userId: {}", userId);

        String companyId = getCompanyIdByUserId(userId);
        log.debug("Retrieved companyId: {} for userId: {}", companyId, userId);

        String workflowId = getCurrentChainId();
        if (workflowId != null) {
            DatabaseProfilerAspect.setWorkflowId(workflowId);
            log.debug("ConversationService에서 chainId 설정: {}", workflowId);
        }

        try {
            String conversationId = UUID.randomUUID().toString();
            Session session = Session.create(userId, conversationId, companyId);
            sessionRepository.save(session);
            log.info("makeConversationId end - conversationId: {}", conversationId);
            return conversationId;
        } catch (Exception e) {
            log.error("Error creating conversation for userId: {}", userId, e);
            throw new RuntimeException("Failed to create conversation", e);
        }
    }

    /**
     * 대화 종료 처리
     */
    @Transactional
    public void endConversation(String conversationId) {
        log.info("endConversation start - conversationId: {}", conversationId);

        try {
            Session session = sessionRepository.findBySessionId(conversationId)
                    .orElseThrow(() -> new IllegalArgumentException("Conversation not found: " + conversationId));
            session.endConversation();
            sessionRepository.save(session);
            log.info("endConversation end - conversationId: {}", conversationId);
        } catch (Exception e) {
            log.error("Error ending conversation: {}", conversationId, e);
            throw new RuntimeException("Failed to end conversation", e);
        }
    }

    /**
     * 대화 상태 업데이트
     */
    @Transactional
    public void updateConversationStatus(String conversationId, Session.SessionStatus status) {
        log.info("updateConversationStatus start - conversationId: {}, status: {}", conversationId, status);

        try {
            Session session = sessionRepository.findBySessionId(conversationId)
                    .orElseThrow(() -> new IllegalArgumentException("Conversation not found: " + conversationId));
            session.updateStatus(status);
            sessionRepository.save(session);
            log.info("updateConversationStatus end - conversationId: {}", conversationId);
        } catch (Exception e) {
            log.error("Error updating conversation status: {}", conversationId, e);
            throw new RuntimeException("Failed to update conversation status", e);
        }
    }

    /**
     * 대화 조회
     */
    public Optional<Session> getConversation(String conversationId) {
        log.info("getConversation - conversationId: {}", conversationId);
        return sessionRepository.findBySessionId(conversationId);
    }

    private String getCurrentChainId() {
        try {
            RequestAttributes requestAttributes = RequestContextHolder.getRequestAttributes();
            if (requestAttributes instanceof ServletRequestAttributes) {
                HttpServletRequest request = ((ServletRequestAttributes) requestAttributes).getRequest();

                Object chainIdAttr = request.getAttribute("chainId");
                if (chainIdAttr != null) {
                    return chainIdAttr.toString();
                }

                Object xChainIdAttr = request.getAttribute("X-Chain-Id");
                if (xChainIdAttr != null) {
                    return xChainIdAttr.toString();
                }
            }
        } catch (Exception e) {
            log.debug("getCurrentChainId 실패: {}", e.getMessage());
        }
        return null;
    }

    /**
     * userId로 companyId 조회 (성능 최적화된 버전)
     */
    private String getCompanyIdByUserId(String userId) {
        log.debug("getCompanyIdByUserId start - userId: {}", userId);

        return usersRepository.findCompanyIdByUserId(userId)
                .orElseThrow(() -> {
                    log.error("User not found or company not assigned for userId: {}", userId);
                    return new IllegalArgumentException("User not found or company not assigned: " + userId);
                });
    }
}