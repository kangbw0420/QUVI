package com.daquv.agent.quvi.repository;

import com.daquv.agent.quvi.entity.Chain;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ChainRepository extends JpaRepository<Chain, String> {

    /**
     * 대화 ID로 체인 목록 조회 (최신순)
     */
    List<Chain> findByConversationConversationIdOrderByChainStartDesc(String conversationId);

    /**
     * 체인 상태로 체인 목록 조회
     */
    List<Chain> findByChainStatus(Chain.ChainStatus status);

    /**
     * 사용자 ID로 체인 목록 조회 (JOIN)
     */
    @Query("SELECT c FROM Chain c JOIN c.conversation conv WHERE conv.userId = :userId ORDER BY c.chainStart DESC")
    List<Chain> findByUserId(@Param("userId") String userId);

    /**
     * 체인 ID로 체인 조회 (대화 정보 포함)
     */
    @Query("SELECT c FROM Chain c JOIN FETCH c.conversation WHERE c.id = :chainId")
    Optional<Chain> findByIdWithConversation(@Param("chainId") String chainId);

    /**
     * 특정 기간 동안의 체인 목록 조회
     */
    @Query("SELECT c FROM Chain c WHERE c.chainStart BETWEEN :startDate AND :endDate")
    List<Chain> findByChainStartBetween(@Param("startDate") java.time.LocalDateTime startDate,
            @Param("endDate") java.time.LocalDateTime endDate);

    /**
     * 완료된 체인의 평균 지속 시간 조회
     */
    @Query("SELECT AVG(EXTRACT(EPOCH FROM (c.chainEnd - c.chainStart))) FROM Chain c WHERE c.chainStatus = 'COMPLETED' AND c.chainEnd IS NOT NULL")
    Double getAverageDurationSeconds();

    Page<Chain> findAllByOrderByChainStartDesc(Pageable pageable);
}