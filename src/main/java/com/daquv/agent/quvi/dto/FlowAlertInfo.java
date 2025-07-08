package com.daquv.agent.quvi.dto;

import com.daquv.agent.quvi.dto.AlertType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
class FlowAlertInfo {
    private String title;
    private String contents;
    private AlertType alertType;
    private String chainId;
    private String userId;
    private LocalDateTime timestamp;
}
