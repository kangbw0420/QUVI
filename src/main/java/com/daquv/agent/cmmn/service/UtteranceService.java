package com.daquv.agent.cmmn.service;

import com.daquv.agent.cmmn.entity.Users;
import com.daquv.agent.cmmn.repository.AuthRepository;
import com.daquv.agent.cmmn.dto.utterance.CreateUtteranceResponseDto;
import com.daquv.agent.cmmn.dto.utterance.GetHistoryResponseDto;
import com.daquv.agent.cmmn.dto.utterance.GetRecommendQuestionResponseDto;
import com.daquv.agent.cmmn.entity.UtteranceHistory;
import com.daquv.agent.cmmn.entity.UtteranceRecommend;
import com.daquv.agent.cmmn.repository.RecommendationQuestionRepository;
import com.daquv.agent.cmmn.repository.UtteranceRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;


@Slf4j
@Service
@RequiredArgsConstructor
public class UtteranceService {
    private final UtteranceRepository utteranceRepository;
    private final AuthRepository authRepository;
    private final RecommendationQuestionRepository recommendationQuestionRepository;

    public CreateUtteranceResponseDto saveUserHistory(String userId, String utteranceContents, String companyId) {
        try {
            log.info("발화 기록 저장 시작 - userId: {}, companyId: {}", userId, companyId);

            // 필수 값 검증
            if (!StringUtils.hasText(utteranceContents)) {
                throw new IllegalArgumentException("utterance_contents는 필수 항목입니다.");
            }

            if (!StringUtils.hasText(userId)) {
                throw new IllegalArgumentException("user_id는 필수 항목입니다.");
            }

            // 엔티티 생성 및 저장
            UtteranceHistory utteranceHistory = UtteranceHistory.builder()
                    .userId(userId)
                    .utteranceContents(utteranceContents)
                    .companyId(companyId) // null 허용
                    .build();

            UtteranceHistory savedHistory = utteranceRepository.save(utteranceHistory);

            log.info("발화 기록 저장 성공 - ID: {}", savedHistory.getSeq());

            return new CreateUtteranceResponseDto(
                    "success",
                    "히스토리가 저장되었습니다.",
                    savedHistory.getSeq()
            );

        } catch (IllegalArgumentException e) {
            log.error("발화 기록 저장 실패 - 잘못된 파라미터: {}", e.getMessage());
            return new CreateUtteranceResponseDto(
                    "error",
                    e.getMessage(),
                    null
            );

        } catch (Exception e) {
            log.error("발화 기록 저장 중 예상치 못한 오류 발생", e);
            return new CreateUtteranceResponseDto(
                    "error",
                    "히스토리 저장에 실패했습니다: " + e.getMessage(),
                    null
            );
        }
    }

    public GetHistoryResponseDto getAllHistory(String userId, String companyId) {
        try {
            log.info("발화 기록 조회 시작 - userId: {}, companyId: {}", userId, companyId);

            if (!StringUtils.hasText(userId)) {
                throw new IllegalArgumentException("user_id는 필수 항목입니다.");
            }

            List<UtteranceHistory> historyList;

            // companyId가 있는지 확인하여 동적 쿼리 실행
            if (StringUtils.hasText(companyId)) {
                log.info("회사 ID 포함 조회: {}", companyId);
                historyList = utteranceRepository.findByUserIdAndCompanyIdOrderByUtteranceDateDesc(userId, companyId);
            } else {
                log.info("전체 발화 기록 조회");
                historyList = utteranceRepository.findByUserIdOrderByUtteranceDateDesc(userId);
            }

            DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

            List<GetHistoryResponseDto.HistoryData> historyDataList = historyList.stream()
                    .map(history -> new GetHistoryResponseDto.HistoryData(
                            history.getUtteranceContents(),
                            history.getUtteranceDate().format(formatter)
                    ))
                    .collect(Collectors.toList());

            log.info("발화 기록 조회 성공 - 조회된 건수: {}", historyDataList.size());

            return new GetHistoryResponseDto("success", historyDataList);

        } catch (Exception e) {
            log.error("발화 기록 조회 중 오류 발생", e);
            return new GetHistoryResponseDto("error", null);
        }
    }

    public GetRecommendQuestionResponseDto getRecommends(String userId, String companyId) {
        try {
            log.info("추천 질문 조회 시작 - userId: {}, companyId: {}", userId, companyId);

            // 사용자 정보 조회하여 effective_company_id 결정 (Python과 동일)
            String effectiveCompanyId = determineEffectiveCompanyId(userId, companyId);

            log.info("사용할 회사 ID: {}", effectiveCompanyId);

            // Python의 get_recommendations 함수와 동일한 로직
            List<String> recommendations = getRecommendations(effectiveCompanyId);

            log.info("추천 질문 조회 완료 - 개수: {}", recommendations.size());

            return new GetRecommendQuestionResponseDto("success", recommendations);

        } catch (Exception e) {
            log.error("추천 질문 조회 중 오류 발생", e);
            return new GetRecommendQuestionResponseDto("error", new ArrayList<>());
        }
    }

    // Python의 get_recommendations 함수를 Java로 변환
    private List<String> getRecommendations(String companyId) {
        try {
            List<UtteranceRecommend> recommendList;

            if (StringUtils.hasText(companyId)) {
                // company_id가 있는 경우
                recommendList = recommendationQuestionRepository.findByCompanyIdOrderByOrderBy(companyId);
                log.info("회사별 추천 질문 조회 - companyId: {}, 조회된 개수: {}", companyId, recommendList.size());
            } else {
                // company_id가 없는 경우 (전체)
                recommendList = recommendationQuestionRepository.findAllByOrderByOrderBy();
                log.info("전체 추천 질문 조회 - 조회된 개수: {}", recommendList.size());
            }

            // Python: [row['utterance_contents'] for row in recommend]
            return recommendList.stream()
                    .map(UtteranceRecommend::getUtteranceContents)
                    .collect(Collectors.toList());

        } catch (Exception e) {
            log.error("추천 질문 조회 중 오류 발생", e);
            return new ArrayList<>(); // Python: "recommend": []
        }
    }

    private String determineEffectiveCompanyId(String userId, String companyId) {
        // companyId 파라미터가 있으면 우선 사용
        if (StringUtils.hasText(companyId)) {
            return companyId;
        }

        // 파라미터가 없으면 사용자의 company_id 조회
        return getUserCompanyId(userId);
    }

    private String getUserCompanyId(String userId) {
        return authRepository.findByUserId(userId)
                .map(Users::getCompanyId)
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다: " + userId));
    }


}
