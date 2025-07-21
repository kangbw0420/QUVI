package com.daquv.agent.quvi.repository;

import com.daquv.agent.quvi.entity.Workflow;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ChainRepository extends JpaRepository<Workflow, String> {

    /**
     * 세션 ID로 체인 목록 조회 (최신순)
     */
    List<Workflow> findBySessionSessionIdOrderByWorkflowStartDesc(String sessionId);

    /**
     * 체인 상태로 체인 목록 조회
     */
    List<Workflow> findByWorkflowStatus(Workflow.WorkflowStatus status);

    /**
     * 사용자 ID로 체인 목록 조회 (JOIN)
     */
    @Query("SELECT c FROM Workflow c JOIN c.session s WHERE s.userId = :userId ORDER BY c.workflowStart DESC")
    List<Workflow> findByUserId(@Param("userId") String userId);

    /**
     * 체인 ID로 체인 조회 (대화 정보 포함)
     */
    @Query("SELECT c FROM Workflow c JOIN FETCH c.session WHERE c.workflowId = :chainId")
    Optional<Workflow> findByIdWithConversation(@Param("chainId") String chainId);

    /**
     * 특정 기간 동안의 체인 목록 조회
     */
    @Query("SELECT c FROM Workflow c WHERE c.workflowStart BETWEEN :startDate AND :endDate")
    List<Workflow> findByWorkflowStartBetween(@Param("startDate") java.time.LocalDateTime startDate,
                                              @Param("endDate") java.time.LocalDateTime endDate);

    /**
     * 완료된 체인의 평균 지속 시간 조회
     */
    @Query("SELECT AVG(EXTRACT(EPOCH FROM (c.workflowEnd - c.workflowStart))) FROM Workflow c WHERE c.workflowStatus = 'COMPLETED' AND c.workflowEnd IS NOT NULL")
    Double getAverageDurationSeconds();

    Page<Workflow> findAllByOrderByWorkflowStartDesc(Pageable pageable);
}