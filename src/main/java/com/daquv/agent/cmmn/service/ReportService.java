package com.daquv.agent.cmmn.service;

import com.daquv.agent.cmmn.dto.report.ChangeReportRequestDto;
import com.daquv.agent.cmmn.dto.report.ChangeReportResponseDto;
import com.daquv.agent.cmmn.dto.report.SaveReportsRequestDto;
import com.daquv.agent.cmmn.dto.report.SaveReportsResponseDto;
import com.daquv.agent.cmmn.entity.UserReports;
import com.daquv.agent.cmmn.repository.UserReportsRepository;
import com.daquv.agent.cmmn.util.BuildSqlStatements;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class ReportService {
    private final UserReportsRepository userReportsRepository;

    private final BuildSqlStatements buildSqlStatements;

    private final FlowService flowService;

    public SaveReportsResponseDto saveUserReport(SaveReportsRequestDto requestDto, String userId) {
        UserReports userReports = UserReports.builder()
                .userId(userId)
                .reportReason(requestDto.getReportReason())
                .answer(requestDto.getAnswer())
                .question(requestDto.getQuestion())
                .sqlQuery(requestDto.getSqlQuery())
                .reportReasonDetail(requestDto.getReportReasonDetail())
                .companyId(requestDto.getCompanyId())
                .build();

        UserReports savedUserReports = userReportsRepository.save(userReports);

        log.info("신고 접수 기록 저장 성공 - ID: {}", savedUserReports.getReportId());

        if (savedUserReports.getReportId() == null) {
            log.error("신고 저장 실패: 결과 없음 또는 report_id 없음. result: {}", savedUserReports.toString());
            return new SaveReportsResponseDto(
                    "error",
                    "신고 접수에 실패했습니다."
            );
        }

        // Flow에 신고 내용 전송
        try {
            flowService.postTask(
                    userId,
                    requestDto.getQuestion(),
                    requestDto.getAnswer(),
                    requestDto.getSqlQuery(),
                    requestDto.getReportReason(),
                    requestDto.getReportReasonDetail()
            );
            log.info("[FLOW] 신고 내용 전송 완료");
        } catch (Exception flowErr) {
            log.error("Flow API error: {}", flowErr.getMessage(), flowErr);
        }

        return new SaveReportsResponseDto(
                "success",
                "신고가 접수되었습니다."
        );
    }

    public ChangeReportResponseDto processDataChange(ChangeReportRequestDto requestDto, String userId) {
        try {
            log.info("데이터 변경 요청 수신: 수정={}, 삭제={}, 추가={}",
                    requestDto.getModified() != null ? requestDto.getModified().size() : 0,
                    requestDto.getDeleted() != null ? requestDto.getDeleted().size() : 0,
                    requestDto.getAdded() != null ? requestDto.getAdded().size() : 0);

            // SQL 문 생성
            Map<String, List<String>> sqlBuckets = buildSqlStatements.buildSqlStatements(
                    requestDto.getModified(),
                    requestDto.getDeleted(),
                    requestDto.getAdded()
            );

            // 유형별 SQL을 구분해서 표시
            StringBuilder sqlQuery = new StringBuilder("\n");

            List<String> insertSqls = sqlBuckets.get("insert");
            if (insertSqls != null && !insertSqls.isEmpty()) {
                sqlQuery.append("\n추가:\n").append(String.join("\n\n", insertSqls));
            }

            List<String> updateSqls = sqlBuckets.get("update");
            if (updateSqls != null && !updateSqls.isEmpty()) {
                sqlQuery.append("\n\n수정:\n").append(String.join("\n\n", updateSqls));
            }

            List<String> deleteSqls = sqlBuckets.get("delete");
            if (deleteSqls != null && !deleteSqls.isEmpty()) {
                sqlQuery.append("\n\n삭제:\n").append(String.join("\n\n", deleteSqls));
            }

            // 상세 요청 정보 생성
            String reportReasonDetail = String.format("수정: %d건, 삭제: %d건, 추가: %d건",
                    requestDto.getModified() != null ? requestDto.getModified().size() : 0,
                    requestDto.getDeleted() != null ? requestDto.getDeleted().size() : 0,
                    requestDto.getAdded() != null ? requestDto.getAdded().size() : 0);

            // Flow로 요청 전송
            try {
                flowService.postTaskDb(userId, requestDto.getChangeReason(),
                        reportReasonDetail, sqlQuery.toString());
            } catch (Exception flowErr) {
                log.error("Flow 알림 전송 중 오류: {}", flowErr.getMessage(), flowErr);
            }

            // 모든 SQL 문을 하나의 리스트로 합치기
            List<String> allSqlStatements = new ArrayList<>();
            if (insertSqls != null) {
                allSqlStatements.addAll(insertSqls);
            }
            if (updateSqls != null) {
                allSqlStatements.addAll(updateSqls);
            }
            if (deleteSqls != null) {
                allSqlStatements.addAll(deleteSqls);
            }

            return new ChangeReportResponseDto(
                    "success",
                    "변경사항이 저장되었고, 알림이 전송되었습니다.",
                    allSqlStatements
            );

        } catch (Exception e) {
            log.error("데이터 변경 저장 중 오류: {}", e.getMessage(), e);
            return new ChangeReportResponseDto(
                    "error",
                    e.getMessage(),
                    new ArrayList<>()
            );
        }
    }
}

