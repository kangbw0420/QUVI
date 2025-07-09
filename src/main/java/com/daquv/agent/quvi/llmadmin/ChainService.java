package com.daquv.agent.quvi.llmadmin;

import com.daquv.agent.quvi.entity.Chain;
import com.daquv.agent.quvi.entity.Conversation;
import com.daquv.agent.quvi.repository.ChainRepository;
import com.daquv.agent.quvi.repository.ConversationRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class ChainService {

    private static final Logger log = LoggerFactory.getLogger(ChainService.class);
    private final ChainRepository chainRepository;
    private final ConversationRepository conversationRepository;

    public ChainService(ChainRepository chainRepository, ConversationRepository conversationRepository) {
        this.chainRepository = chainRepository;
        this.conversationRepository = conversationRepository;
    }

    /**
     * 새로운 체인을 생성하고 초기 상태를 기록
     * 
     * @param conversationId 대화 ID
     * @param userQuestion 사용자 질문
     * @return 생성된 chain ID
     */
    @Transactional
    public String createChain(String conversationId, String userQuestion) {
        log.info("createChain start - conversationId: {}, userQuestion: {}", conversationId, userQuestion);
        
        try {
            String chainId = UUID.randomUUID().toString();
            
            // Conversation 조회
            Conversation conversation = conversationRepository.findByConversationId(conversationId)
                    .orElseThrow(() -> new IllegalArgumentException("Conversation not found: " + conversationId));
            
            // Chain 생성
            Chain chain = Chain.create(chainId, conversation, userQuestion, Chain.ChainStatus.active);
            
            chainRepository.save(chain);
            
            log.info("createChain end - chainId: {}", chainId);
            return chainId;
            
        } catch (Exception e) {
            log.error("Error in createChain - conversationId: {}, userQuestion: {}", conversationId, userQuestion, e);
            throw new RuntimeException("Failed to create chain", e);
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
    public boolean completeChain(String chainId, String finalAnswer) {
        log.info("completeChain start - chainId: {}, finalAnswer: {}", chainId, finalAnswer);
        
        try {
            Chain chain = chainRepository.findById(chainId)
                    .orElseThrow(() -> new IllegalArgumentException("Chain not found: " + chainId));
            
            chain.completeChain(finalAnswer);
            chainRepository.save(chain);
            
            log.info("completeChain end - chainId: {}", chainId);
            return true;
            
        } catch (Exception e) {
            log.error("Error in completeChain - chainId: {}, finalAnswer: {}", chainId, finalAnswer, e);
            throw new RuntimeException("Failed to complete chain", e);
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
        try {
            Chain chain = chainRepository.findById(chainId)
                    .orElseThrow(() -> new RuntimeException("Chain not found: " + chainId));

            chain.markError(errorMessage, errorLog);
            chainRepository.saveAndFlush(chain); // 즉시 DB에 반영

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
        try {
            Chain chain = chainRepository.findById(chainId)
                    .orElseThrow(() -> new RuntimeException("Chain not found: " + chainId));

            chain.addChainLog(chainLogText);
            chainRepository.saveAndFlush(chain); // 즉시 DB에 반영

            log.info("✅ 체인 로그 업데이트 완료 - chainId: {}", chainId);
        } catch (Exception e) {
            log.error("❌ 체인 로그 업데이트 실패 - chainId: {}, error: {}", chainId, e.getMessage(), e);
            throw new RuntimeException("Failed to update chain log", e);
        }
    }
}
