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
     * 현재 trace와 같은 chain_id를 가진 직전 trace의 state를 조회
     */
    @Query("SELECT s FROM State s " +
           "JOIN s.trace t " +
           "WHERE t.chain.id = (" +
           "    SELECT tr.chain.id " +
           "    FROM Trace tr " +
           "    WHERE tr.id = :traceId" +
           ") " +
           "AND t.id != :traceId " +
           "ORDER BY t.traceStart DESC, s.id DESC")
    List<State> findLatestStatesByTraceId(@Param("traceId") String traceId);

    /**
     * 트레이스 ID로 최신 상태 조회
     */
    @Query("SELECT s FROM State s WHERE s.trace.id = :traceId ORDER BY s.id DESC")
    Optional<State> findLatestByTraceId(@Param("traceId") String traceId);

    /**
     * 체인 ID로 상태 목록 조회
     */
    @Query("SELECT s FROM State s JOIN s.trace t WHERE t.chain.id = :chainId ORDER BY t.traceStart ASC")
    List<State> findByChainId(@Param("chainId") String chainId);

    /**
     * 선택된 API로 상태 목록 조회
     */
    List<State> findBySelectedApi(String selectedApi);

    /**
     * table_pipe로 상태 목록 조회
     */
    List<State> findByTablePipe(String tablePipe);
}