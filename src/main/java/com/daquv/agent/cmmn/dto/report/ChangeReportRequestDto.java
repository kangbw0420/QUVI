package com.daquv.agent.cmmn.dto.report;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class ChangeReportRequestDto {
    private List<Map<String, Object>> modified;
    private List<Map<String, Object>> deleted;  // DeletedItem 대신 Map으로 처리
    private List<Map<String, Object>> added;
    private String changeReason;
}
