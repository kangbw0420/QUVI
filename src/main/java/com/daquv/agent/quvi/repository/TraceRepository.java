package com.daquv.agent.quvi.repository;

import com.daquv.agent.quvi.entity.Node;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface TraceRepository extends JpaRepository<Node, String> {

    /**
     * 체인 ID로 트레이스 목록 조회
     */
    @Query("SELECT n FROM Node n WHERE n.workflow.workflowId = :workflowId ORDER BY n.nodeStart ASC")
    List<Node> findByWorkflowIdOrderByNodeStartAsc(@Param("workflowId") String workflowId);

    /**
     * 트레이스 상태로 트레이스 목록 조회
     */
    @Query("SELECT n FROM Node n WHERE n.nodeStatus = :status")
    List<Node> findByNodeStatus(Node.NodeStatus status);

    /**
     * 노드 타입으로 트레이스 목록 조회
     */
    @Query("SELECT n FROM Node n WHERE n.nodeName = :nodeName")
    List<Node> findByNodeName(@Param("nodeName")String nodeName);

//    /**
//     * 트레이스 ID로 트레이스 조회 (체인 정보 포함)
//     */
//    @Query("SELECT t FROM Node t JOIN FETCH t.chain WHERE t.id = :traceId")
//    Optional<Node> findByIdWithNode(@Param("traceId") String traceId);
//
//    /**
//     * 특정 기간 동안의 트레이스 목록 조회
//     */
//    @Query("SELECT t FROM Node t WHERE t.traceStart BETWEEN :startDate AND :endDate")
//    List<Node> findByTraceStartBetween(@Param("startDate") java.time.LocalDateTime startDate,
//                                       @Param("endDate") java.time.LocalDateTime endDate);
//
//    /**
//     * 완료된 트레이스의 평균 지속 시간 조회
//     */
//    @Query("SELECT AVG(EXTRACT(EPOCH FROM (t.traceEnd - t.traceStart))) FROM Trace t WHERE t.traceStatus = 'COMPLETED' AND t.traceEnd IS NOT NULL")
//    Double getAverageDurationSeconds();
} 