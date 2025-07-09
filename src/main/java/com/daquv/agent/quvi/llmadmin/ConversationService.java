package com.daquv.agent.quvi.llmadmin;

import com.daquv.agent.quvi.entity.Conversation;
import com.daquv.agent.quvi.repository.ConversationRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;
import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class ConversationService {

    private static final Logger log = LoggerFactory.getLogger(ConversationService.class);
    private final ConversationRepository conversationRepository;

    public ConversationService(ConversationRepository conversationRepository) {
        this.conversationRepository = conversationRepository;
    }

    /**
     * conversation_id가 존재하고 status가 active인지 확인
     * 
     * @param conversationId 대화 ID
     * @return conversation이 존재하고 active면 true, 그 외는 false
     */
    public boolean checkConversationId(String conversationId) {
        log.info("checkConversationId start - conversationId: {}", conversationId);
        try {
            return conversationRepository.findByConversationId(conversationId)
                    .map(conversation -> Conversation.ConversationStatus.active.equals(conversation.getConversationStatus()))
                    .orElse(false);
        } catch (Exception e) {
            log.error("Error checking conversation ID: {}", conversationId, e);
            return false;
        }
    }

    /**
     * 새로운 conversation 생성. UUID로 ID 생성하고 status는 active로 설정
     * 
     * @param userId 사용자 ID
     * @return 생성된 conversation ID
     */
    @Transactional
    public String makeConversationId(String userId) {
        log.info("makeConversationId start - userId: {}", userId);
        try {
            String conversationId = UUID.randomUUID().toString();
            Conversation conversation = Conversation.create(userId, conversationId);
            conversationRepository.save(conversation);
            log.info("makeConversationId end - conversationId: {}", conversationId);
            return conversationId;
        } catch (Exception e) {
            log.error("Error creating conversation for userId: {}", userId, e);
            throw new RuntimeException("Failed to create conversation", e);
        }
    }

    /**
     * 대화 종료 처리
     * 
     * @param conversationId 대화 ID
     */
    @Transactional
    public void endConversation(String conversationId) {
        log.info("endConversation start - conversationId: {}", conversationId);
        try {
            Conversation conversation = conversationRepository.findByConversationId(conversationId)
                    .orElseThrow(() -> new IllegalArgumentException("Conversation not found: " + conversationId));
            conversation.endConversation();
            conversationRepository.save(conversation);
            log.info("endConversation end - conversationId: {}", conversationId);
        } catch (Exception e) {
            log.error("Error ending conversation: {}", conversationId, e);
            throw new RuntimeException("Failed to end conversation", e);
        }
    }

    /**
     * 대화 상태 업데이트
     * 
     * @param conversationId 대화 ID
     * @param status 새로운 상태
     */
    @Transactional
    public void updateConversationStatus(String conversationId, Conversation.ConversationStatus status) {
        log.info("updateConversationStatus start - conversationId: {}, status: {}", conversationId, status);
        try {
            Conversation conversation = conversationRepository.findByConversationId(conversationId)
                    .orElseThrow(() -> new IllegalArgumentException("Conversation not found: " + conversationId));
            conversation.updateStatus(status);
            conversationRepository.save(conversation);
            log.info("updateConversationStatus end - conversationId: {}", conversationId);
        } catch (Exception e) {
            log.error("Error updating conversation status: {}", conversationId, e);
            throw new RuntimeException("Failed to update conversation status", e);
        }
    }

    /**
     * 대화 조회
     * 
     * @param conversationId 대화 ID
     * @return 대화 정보 (Optional)
     */
    public Optional<Conversation> getConversation(String conversationId) {
        log.info("getConversation - conversationId: {}", conversationId);
        return conversationRepository.findByConversationId(conversationId);
    }
} 