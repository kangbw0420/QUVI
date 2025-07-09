package com.daquv.agent.quvi.repository;

import com.daquv.agent.quvi.entity.Qna;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface QnaRepository extends JpaRepository<Qna, String> {

    /**
     * 트레이스 ID로 QnA 목록 조회 (시간순)
     */
    List<Qna> findByTraceIdOrderByQuestionTimestampAsc(String traceId);

    /**
     * 모델로 QnA 목록 조회
     */
    List<Qna> findByModel(String model);

    /**
     * 답변이 있는 QnA 목록 조회
     */
    List<Qna> findByAnswerIsNotNull();

    /**
     * QnA ID로 QnA 조회 (트레이스 정보 포함)
     */
    @Query("SELECT q FROM Qna q JOIN FETCH q.trace WHERE q.id = :qnaId")
    Optional<Qna> findByIdWithTrace(@Param("qnaId") String qnaId);

    /**
     * 특정 기간 동안의 QnA 목록 조회
     */
    @Query("SELECT q FROM Qna q WHERE q.questionTimestamp BETWEEN :startDate AND :endDate")
    List<Qna> findByQuestionTimestampBetween(@Param("startDate") java.time.LocalDateTime startDate,
                                            @Param("endDate") java.time.LocalDateTime endDate);

    /**
     * 모델별 QnA 수 조회
     */
    long countByModel(String model);

    /**
     * 답변이 있는 QnA 수 조회
     */
    long countByAnswerIsNotNull();

    /**
     * 평균 검색 시간 조회
     */
    @Query("SELECT AVG(q.retrieveTime) FROM Qna q WHERE q.retrieveTime IS NOT NULL")
    java.math.BigDecimal getAverageRetrieveTime();
} 