package com.daquv.agent.quvi.repository;

import com.daquv.agent.quvi.entity.Fewshot;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface FewshotRepository extends JpaRepository<Fewshot, String> {

    /**
     * QnA ID로 Fewshot 목록 조회 (순서대로)
     */
    List<Fewshot> findByQnaIdOrderByOrderSeqAsc(String qnaId);

    /**
     * Fewshot ID로 Fewshot 조회 (QnA 정보 포함)
     */
    @Query("SELECT f FROM Fewshot f JOIN FETCH f.qna WHERE f.id = :fewshotId")
    Optional<Fewshot> findByIdWithQna(@Param("fewshotId") String fewshotId);

    /**
     * 특정 기간 동안의 Fewshot 목록 조회
     */
    @Query("SELECT f FROM Fewshot f WHERE f.createdAt BETWEEN :startDate AND :endDate")
    List<Fewshot> findByCreatedAtBetween(@Param("startDate") java.time.LocalDateTime startDate,
                                        @Param("endDate") java.time.LocalDateTime endDate);

    /**
     * QnA별 Fewshot 개수 조회
     */
    long countByQnaId(String qnaId);

    /**
     * 특정 QnA의 Fewshot 순서별 개수 조회
     */
    @Query("SELECT f.orderSeq, COUNT(f) FROM Fewshot f WHERE f.qna.id = :qnaId GROUP BY f.orderSeq")
    List<Object[]> countByQnaIdGroupByOrderSeq(@Param("qnaId") String qnaId);
} 