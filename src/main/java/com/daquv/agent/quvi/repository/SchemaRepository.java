package com.daquv.agent.quvi.repository;

import com.daquv.agent.quvi.entity.Schema;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface SchemaRepository extends JpaRepository<Schema, Long> {

    /**
     * 모든 스키마 조회
     */
    List<Schema> findAllByOrderByIdAsc();

    /**
     * 테이블명으로 스키마 조회
     */
    Optional<Schema> findByTableNm(String tableNm);

    /**
     * 테이블명으로 스키마 존재 여부 확인
     */
    boolean existsByTableNm(String tableNm);

    /**
     * 프롬프트 업데이트
     */
    @Modifying
    @Query("UPDATE Schema s SET s.prompt = :prompt WHERE s.id = :id")
    int updatePromptById(@Param("id") Long id, @Param("prompt") String prompt);

    /**
     * 테이블명으로 프롬프트 업데이트
     */
    @Modifying
    @Query("UPDATE Schema s SET s.prompt = :prompt WHERE s.tableNm = :tableNm")
    int updatePromptByTableNm(@Param("tableNm") String tableNm, @Param("prompt") String prompt);
} 