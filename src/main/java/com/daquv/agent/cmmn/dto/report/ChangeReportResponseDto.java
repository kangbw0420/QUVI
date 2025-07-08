package com.daquv.agent.cmmn.dto.report;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.List;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class ChangeReportResponseDto {
    private String status;

    private String message;

    private List<String> sqlStatements;
}
