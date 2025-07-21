package com.daquv.agent.quvi.repository;

import com.daquv.agent.quvi.entity.BaseState;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.NoRepositoryBean;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

@NoRepositoryBean
public interface BaseStateRepository<T extends BaseState> extends JpaRepository<T, Long> {

    /**
     * 트레이스 ID로 상태 목록 조회
     */
    @Query("SELECT s FROM State s WHERE s.node.nodeId = :traceId ORDER BY s.id ASC")
    List<T> findByTraceIdOrderByIdAsc(@Param("traceId") String traceId);

    /**
     * 회사 ID로 상태 목록 조회
     */
    @Query("SELECT s FROM State s WHERE s.companyId = :companyId")
    List<T> findByCompanyId(@Param("companyId") String companyId);

    /**
     * 선택된 테이블로 상태 목록 조회
     */
    @Query("SELECT s FROM State s WHERE s.selectedTable = :selectedTable")
    List<T> findBySelectedTable(@Param("selectedTable") String selectedTable);

    /**
     * SQL 에러가 있는 상태 목록 조회
     */
    @Query("SELECT s FROM State s WHERE s.sqlError IS NOT NULL")
    List<T> findBySqlErrorIsNotNull();

    /**
     * 상태 ID로 상태 조회 (트레이스 정보 포함)
     */
    @Query("SELECT s FROM State s JOIN FETCH s.node WHERE s.id = :stateId")
    Optional<T> findByIdWithTrace(@Param("stateId") Long stateId);

    /**
     * 특정 회사의 상태 수 조회
     */
    @Query("SELECT COUNT(s) FROM State s WHERE s.companyId = :companyId")
    long countByCompanyId(@Param("companyId") String companyId);

    /**
     * SQL 에러가 있는 상태 수 조회
     */
    @Query("SELECT COUNT(s) FROM State s WHERE s.sqlError IS NOT NULL")
    long countBySqlErrorIsNotNull();

    /**
     * 회사별 평균 행 수 조회
     */
    @Query("SELECT AVG(s.totalRows) FROM State s WHERE s.companyId = :companyId AND s.totalRows IS NOT NULL")
    Double getAverageTotalRowsByCompanyId(@Param("companyId") String companyId);
}