package com.daquv.agent.quvi.repository;

import com.daquv.agent.quvi.entity.Session;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ConversationRepository extends JpaRepository<Session, String> {

    /**
     * 사용자 ID로 대화 목록 조회 (최신순)
     */
    List<Session> findByUserIdOrderByConversationStartDesc(String userId);

    /**
     * 세션 ID로 대화 조회 (conversationId -> sessionId로 변경)
     */
    Optional<Session> findBySessionId(String sessionId);

    /**
     * 사용자 ID로 대화 존재 여부 확인
     */
    boolean existsByUserId(String userId);

    /**
     * 대화 상태로 대화 목록 조회
     */
    List<Session> findByConversationStatus(Session.SessionStatus status);

    /**
     * 사용자별 대화 수 조회
     */
    long countByUserId(String userId);

    /**
     * 특정 기간 동안의 대화 목록 조회
     */
    @Query("SELECT s FROM Session s WHERE s.conversationStart BETWEEN :startDate AND :endDate")
    List<Session> findByConversationStartBetween(@Param("startDate") java.time.LocalDateTime startDate,
                                                 @Param("endDate") java.time.LocalDateTime endDate);
}