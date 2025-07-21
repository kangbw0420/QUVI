//package com.daquv.agent.quvi.repository;
//
//import com.daquv.agent.quvi.entity.Fewshot;
//import org.springframework.data.jpa.repository.JpaRepository;
//import org.springframework.data.jpa.repository.Query;
//import org.springframework.data.repository.query.Param;
//import org.springframework.stereotype.Repository;
//
//import java.util.List;
//import java.util.Optional;
//
//@Repository
//public interface FewshotRepository extends JpaRepository<Fewshot, String> {
//
//    /**
//     * QnA ID로 Fewshot 목록 조회 (순서대로) - qna -> generation으로 수정
//     */
//    @Query("SELECT f FROM Fewshot f WHERE f.generation.id = :qnaId ORDER BY f.orderSeq ASC")
//    List<Fewshot> findByQnaIdOrderByOrderSeqAsc(@Param("qnaId") String qnaId);
//
//    /**
//     * 기존 코드 호환성을 위한 별칭 메서드
//     */
//    default List<Fewshot> findByGenerationIdOrderByOrderSeqAsc(String generationId) {
//        return findByQnaIdOrderByOrderSeqAsc(generationId);
//    }
//
//    /**
//     * Fewshot ID로 Fewshot 조회 (QnA 정보 포함) - qna -> generation으로 수정
//     */
//    @Query("SELECT f FROM Fewshot f JOIN FETCH f.generation WHERE f.id = :fewshotId")
//    Optional<Fewshot> findByIdWithQna(@Param("fewshotId") String fewshotId);
//
//    /**
//     * 기존 코드 호환성을 위한 별칭 메서드
//     */
//    default Optional<Fewshot> findByIdWithGeneration(String fewshotId) {
//        return findByIdWithQna(fewshotId);
//    }
//
//    /**
//     * 특정 기간 동안의 Fewshot 목록 조회
//     */
//    @Query("SELECT f FROM Fewshot f WHERE f.createdAt BETWEEN :startDate AND :endDate")
//    List<Fewshot> findByCreatedAtBetween(@Param("startDate") java.time.LocalDateTime startDate,
//                                         @Param("endDate") java.time.LocalDateTime endDate);
//
//    /**
//     * QnA별 Fewshot 개수 조회 - qna -> generation으로 수정
//     */
//    @Query("SELECT COUNT(f) FROM Fewshot f WHERE f.generation.id = :qnaId")
//    long countByQnaId(@Param("qnaId") String qnaId);
//
//    /**
//     * 기존 코드 호환성을 위한 별칭 메서드
//     */
//    default long countByGenerationId(String generationId) {
//        return countByQnaId(generationId);
//    }
//
//    /**
//     * 특정 QnA의 Fewshot 순서별 개수 조회 - qna -> generation으로 수정
//     */
//    @Query("SELECT f.orderSeq, COUNT(f) FROM Fewshot f WHERE f.generation.id = :qnaId GROUP BY f.orderSeq")
//    List<Object[]> countByQnaIdGroupByOrderSeq(@Param("qnaId") String qnaId);
//
//    /**
//     * 기존 코드 호환성을 위한 별칭 메서드
//     */
//    default List<Object[]> countByGenerationIdGroupByOrderSeq(String generationId) {
//        return countByQnaIdGroupByOrderSeq(generationId);
//    }
//}