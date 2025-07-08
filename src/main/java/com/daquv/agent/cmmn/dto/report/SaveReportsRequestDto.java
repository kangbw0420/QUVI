package com.daquv.agent.cmmn.dto.report;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class SaveReportsRequestDto {
    private String userId;

    private String question;

    private String answer;

    @JsonProperty("sql_query")
    private String sqlQuery;

    @JsonProperty("report_reason")
    private String reportReason;

    @JsonProperty("report_reason_detail")
    private String reportReasonDetail;

    @JsonProperty("company_id")
    private String companyId;
}
