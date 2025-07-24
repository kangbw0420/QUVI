package com.daquv.agent.workflow.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class MetricFlowRequestDto {
    private List<String> metrics;
    @JsonProperty("group_by")
    private List<String> groupBy;
    private List<String> filters;
    @JsonProperty("order_by")
    private List<String> orderBy;
    private Integer limit;
}