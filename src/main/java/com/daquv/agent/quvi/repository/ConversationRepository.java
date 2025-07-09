package com.daquv.agent.quvi.repository;

import com.daquv.agent.quvi.entity.Conversation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ConversationRepository extends JpaRepository<Conversation, Long> {

    /**
     * 사용자 ID로 대화 목록 조회 (최신순)
     */
    List<Conversation> findByUserIdOrderByConversationStartDesc(String userId);

    /**
     * 대화 ID로 대화 조회
     */
    Optional<Conversation> findByConversationId(String conversationId);

    /**
     * 사용자 ID로 대화 존재 여부 확인
     */
    boolean existsByUserId(String userId);

    /**
     * 대화 상태로 대화 목록 조회
     */
    List<Conversation> findByConversationStatus(Conversation.ConversationStatus status);

    /**
     * 사용자별 대화 수 조회
     */
    long countByUserId(String userId);

    /**
     * 특정 기간 동안의 대화 목록 조회
     */
    @Query("SELECT c FROM Conversation c WHERE c.conversationStart BETWEEN :startDate AND :endDate")
    List<Conversation> findByConversationStartBetween(@Param("startDate") java.time.LocalDateTime startDate,
                                                     @Param("endDate") java.time.LocalDateTime endDate);
} 