package com.daquv.agent.quvi.repository;

import com.daquv.agent.quvi.entity.Trace;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface TraceRepository extends JpaRepository<Trace, String> {

    /**
     * 체인 ID로 트레이스 목록 조회
     */
    List<Trace> findByChainIdOrderByTraceStartAsc(String chainId);

    /**
     * 트레이스 상태로 트레이스 목록 조회
     */
    List<Trace> findByTraceStatus(Trace.TraceStatus status);

    /**
     * 노드 타입으로 트레이스 목록 조회
     */
    List<Trace> findByNodeType(String nodeType);

    /**
     * 트레이스 ID로 트레이스 조회 (체인 정보 포함)
     */
    @Query("SELECT t FROM Trace t JOIN FETCH t.chain WHERE t.id = :traceId")
    Optional<Trace> findByIdWithChain(@Param("traceId") String traceId);

    /**
     * 특정 기간 동안의 트레이스 목록 조회
     */
    @Query("SELECT t FROM Trace t WHERE t.traceStart BETWEEN :startDate AND :endDate")
    List<Trace> findByTraceStartBetween(@Param("startDate") java.time.LocalDateTime startDate,
                                       @Param("endDate") java.time.LocalDateTime endDate);

    /**
     * 완료된 트레이스의 평균 지속 시간 조회
     */
    @Query("SELECT AVG(EXTRACT(EPOCH FROM (t.traceEnd - t.traceStart))) FROM Trace t WHERE t.traceStatus = 'COMPLETED' AND t.traceEnd IS NOT NULL")
    Double getAverageDurationSeconds();
} 