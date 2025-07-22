package com.daquv.agent.repository;

import com.daquv.agent.entity.State;
import com.daquv.agent.quvi.repository.BaseStateRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface StateRepository extends BaseStateRepository<State> {

    /**
     * 현재 trace와 같은 workflow_id를 가진 직전 trace의 state를 조회
     */
    @Query("SELECT s FROM State s " +
            "JOIN s.node t " +
            "WHERE t.workflow.workflowId = (" +
            "    SELECT tr.workflow.workflowId " +
            "    FROM Node tr " +
            "    WHERE tr.nodeId = :nodeId" +
            ") " +
            "AND t.nodeId != :nodeId " +
            "ORDER BY t.nodeStart DESC, s.id DESC")
    List<State> findLatestStatesByTraceId(@Param("nodeId") String nodeId);

    /**
     * 트레이스 ID로 최신 상태 조회
     */
    @Query("SELECT s FROM State s WHERE s.node.nodeId = :nodeId ORDER BY s.id DESC")
    Optional<State> findLatestByTraceId(@Param("nodeId") String nodeId);

    /**
     * 체인 ID로 상태 목록 조회
     */
    @Query("SELECT s FROM State s JOIN s.node t WHERE t.workflow.workflowId = :workflowId ORDER BY t.nodeStart ASC")
    List<State> findByChainId(@Param("workflowId") String workflowId);

    /**
     * 선택된 API로 상태 목록 조회
     */
    List<State> findBySelectedApi(String selectedApi);

    /**
     * table_pipe로 상태 목록 조회
     */
    List<State> findByTablePipe(String tablePipe);
}