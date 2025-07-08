package com.daquv.agent.cmmn.repository;

import com.daquv.agent.cmmn.entity.UtteranceRecommend;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface RecommendationQuestionRepository extends JpaRepository<UtteranceRecommend, Long> {

    // 특정 회사의 추천 질문 조회 (order_by 순)
    List<UtteranceRecommend> findByCompanyIdOrderByOrderBy(String companyId);

    // 전체 추천 질문 조회 (company_id 조건 없이)
    List<UtteranceRecommend> findAllByOrderByOrderBy();
}
