package com.daquv.agent.quvi.llmadmin;

import com.daquv.agent.quvi.entity.Conversation;
import com.daquv.agent.quvi.repository.ConversationRepository;
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
public class ConversationService {

    private static final Logger log = LoggerFactory.getLogger(ConversationService.class);
    private final ConversationRepository conversationRepository;

    @Autowired
    private RequestProfiler requestProfiler;

    public ConversationService(ConversationRepository conversationRepository) {
        this.conversationRepository = conversationRepository;
    }

    /**
     * conversation_id가 존재하고 status가 active인지 확인
     */
    public boolean checkConversationId(String conversationId) {
        log.info("checkConversationId start - conversationId: {}", conversationId);

        String chainId = getCurrentChainId();
        long startTime = System.currentTimeMillis();
        try {
            return conversationRepository.findByConversationId(conversationId)
                    .map(conversation -> Conversation.ConversationStatus.active.equals(conversation.getConversationStatus()))
                    .orElse(false);
        } catch (Exception e) {
            log.error("Error checking conversation ID: {}", conversationId, e);
            return false;
        } finally {
            // DB 프로파일링 기록
            long endTime = System.currentTimeMillis();
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordDbCall(chainId, elapsedTime, false, "conversation_service");
        }
    }

    /**
     * 새로운 conversation 생성. UUID로 ID 생성하고 status는 active로 설정
     */
    @Transactional
    public String makeConversationId(String userId) {
        log.info("makeConversationId start - userId: {}", userId);

        String chainId = getCurrentChainId();
        if (chainId != null) {
            DatabaseProfilerAspect.setChainId(chainId);
            log.debug("ConversationService에서 chainId 설정: {}", chainId);
        }

        long startTime = System.currentTimeMillis();
        try {
            String conversationId = UUID.randomUUID().toString();
            Conversation conversation = Conversation.create(userId, conversationId);
            conversationRepository.save(conversation);
            log.info("makeConversationId end - conversationId: {}", conversationId);
            return conversationId;
        } catch (Exception e) {
            log.error("Error creating conversation for userId: {}", userId, e);
            throw new RuntimeException("Failed to create conversation", e);
        } finally {
            // DB 프로파일링 기록
            long endTime = System.currentTimeMillis();
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordDbCall(chainId, elapsedTime, false, "conversation_service");
        }
    }

    /**
     * 대화 종료 처리
     */
    @Transactional
    public void endConversation(String conversationId) {
        log.info("endConversation start - conversationId: {}", conversationId);

        String chainId = getCurrentChainId();
        long startTime = System.currentTimeMillis();
        try {
            Conversation conversation = conversationRepository.findByConversationId(conversationId)
                    .orElseThrow(() -> new IllegalArgumentException("Conversation not found: " + conversationId));
            conversation.endConversation();
            conversationRepository.save(conversation);
            log.info("endConversation end - conversationId: {}", conversationId);
        } catch (Exception e) {
            log.error("Error ending conversation: {}", conversationId, e);
            throw new RuntimeException("Failed to end conversation", e);
        } finally {
            // DB 프로파일링 기록
            long endTime = System.currentTimeMillis();
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordDbCall(chainId, elapsedTime, false, "conversation_service");
        }
    }

    /**
     * 대화 상태 업데이트
     */
    @Transactional
    public void updateConversationStatus(String conversationId, Conversation.ConversationStatus status) {
        log.info("updateConversationStatus start - conversationId: {}, status: {}", conversationId, status);

        String chainId = getCurrentChainId();
        long startTime = System.currentTimeMillis();
        try {
            Conversation conversation = conversationRepository.findByConversationId(conversationId)
                    .orElseThrow(() -> new IllegalArgumentException("Conversation not found: " + conversationId));
            conversation.updateStatus(status);
            conversationRepository.save(conversation);
            log.info("updateConversationStatus end - conversationId: {}", conversationId);
        } catch (Exception e) {
            log.error("Error updating conversation status: {}", conversationId, e);
            throw new RuntimeException("Failed to update conversation status", e);
        } finally {
            // DB 프로파일링 기록
            long endTime = System.currentTimeMillis();
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordDbCall(chainId, elapsedTime, false, "conversation_service");
        }
    }

    /**
     * 대화 조회
     */
    public Optional<Conversation> getConversation(String conversationId) {
        log.info("getConversation - conversationId: {}", conversationId);

        String chainId = getCurrentChainId();
        long startTime = System.currentTimeMillis();
        try {
            return conversationRepository.findByConversationId(conversationId);
        } finally {
            // DB 프로파일링 기록
            long endTime = System.currentTimeMillis();
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordDbCall(chainId, elapsedTime, false, "conversation_service");
        }
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
}