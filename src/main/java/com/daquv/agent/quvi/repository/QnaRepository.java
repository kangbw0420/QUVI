package com.daquv.agent.quvi.repository;

import com.daquv.agent.quvi.entity.Generation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface QnaRepository extends JpaRepository<Generation, String> {

    /**
     * 트레이스 ID로 QnA 목록 조회 (시간순) - Node의 nodeId 사용
     */
    @Query("SELECT q FROM Generation q WHERE q.node.nodeId = :traceId ORDER BY q.questionTimestamp ASC")
    List<Generation> findByTraceIdOrderByQuestionTimestampAsc(@Param("traceId") String traceId);

    /**
     * 모델로 QnA 목록 조회
     */
    List<Generation> findByModel(String model);

    /**
     * 답변이 있는 QnA 목록 조회 (answer -> output으로 수정)
     */
    List<Generation> findByOutputIsNotNull();

    /**
     * 기존 코드 호환성을 위한 별칭 메서드
     */
    default List<Generation> findByAnswerIsNotNull() {
        return findByOutputIsNotNull();
    }

    /**
     * QnA ID로 QnA 조회 (트레이스 정보 포함) - Node로 수정
     */
    @Query("SELECT q FROM Generation q JOIN FETCH q.node WHERE q.id = :qnaId")
    Optional<Generation> findByIdWithTrace(@Param("qnaId") String qnaId);

    /**
     * 특정 기간 동안의 QnA 목록 조회
     */
    @Query("SELECT q FROM Generation q WHERE q.questionTimestamp BETWEEN :startDate AND :endDate")
    List<Generation> findByQuestionTimestampBetween(@Param("startDate") java.time.LocalDateTime startDate,
                                                    @Param("endDate") java.time.LocalDateTime endDate);

    /**
     * 모델별 QnA 수 조회
     */
    long countByModel(String model);

    /**
     * 답변이 있는 QnA 수 조회 (answer -> output으로 수정)
     */
    long countByOutputIsNotNull();

    /**
     * 기존 코드 호환성을 위한 별칭 메서드
     */
    default long countByAnswerIsNotNull() {
        return countByOutputIsNotNull();
    }

    /**
     * 평균 검색 시간 조회 (retrieveTime 필드가 Generation에 없으므로 주석 처리)
     */
    // @Query("SELECT AVG(q.retrieveTime) FROM Generation q WHERE q.retrieveTime IS NOT NULL")
    // java.math.BigDecimal getAverageRetrieveTime();
}