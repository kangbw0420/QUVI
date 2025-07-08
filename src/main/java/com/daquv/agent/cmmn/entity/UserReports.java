package com.daquv.agent.cmmn.entity;

import java.time.LocalDateTime;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Table;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@NoArgsConstructor
@AllArgsConstructor
@Table(name = "user_reports")
@Builder
@Getter
public class UserReports {
    @Id
    @Column(name = "report_id", columnDefinition = "serial")
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long reportId;

    private String userId;

    @Column(name = "question", columnDefinition = "TEXT")
    private String question;

    @Column(columnDefinition = "TEXT")
    private String answer;

    @Column(columnDefinition = "TEXT")
    private String reportReason;

    private String companyId;

    private LocalDateTime createdAt;

    private String status;

    @Column(columnDefinition = "TEXT")
    private String sqlQuery;

    @Column(columnDefinition = "TEXT")
    private String reportReasonDetail;
}
