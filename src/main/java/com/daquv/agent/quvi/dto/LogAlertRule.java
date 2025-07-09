package com.daquv.agent.quvi.dto;

import com.daquv.agent.quvi.dto.AlertType;
import com.daquv.agent.quvi.logging.ChainLogContext;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.function.Predicate;

/**
 * 로그 알림 규칙
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LogAlertRule {

    private String ruleName;
    private String description;
    private Predicate<ChainLogEntry> condition;
    private Predicate<ChainLogContext> contextCondition;
    private AlertType alertType;
    private boolean enabled;

    /**
     * 규칙 매칭 확인
     */
    public boolean matches(ChainLogContext context, ChainLogEntry entry) {
        if (!enabled) return false;

        boolean entryMatches = condition == null || condition.test(entry);
        boolean contextMatches = contextCondition == null || contextCondition.test(context);

        return entryMatches && contextMatches;
    }
}