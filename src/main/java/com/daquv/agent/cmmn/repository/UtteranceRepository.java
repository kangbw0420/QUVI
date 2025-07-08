package com.daquv.agent.cmmn.repository;

import com.daquv.agent.cmmn.entity.UtteranceHistory;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface UtteranceRepository extends JpaRepository<UtteranceHistory, Long> {
    // 사용자 ID로 발화 기록 조회 (최신순)
    List<UtteranceHistory> findByUserIdOrderByUtteranceDateDesc(String userId);

    // 사용자 ID와 회사 ID로 발화 기록 조회 (최신순)
    List<UtteranceHistory> findByUserIdAndCompanyIdOrderByUtteranceDateDesc(String userId, String companyId);
}
