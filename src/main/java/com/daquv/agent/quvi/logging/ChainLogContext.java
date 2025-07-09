package com.daquv.agent.quvi.logging;

import com.daquv.agent.quvi.dto.ChainLogEntry;
import com.daquv.agent.quvi.dto.LogLevel;
import com.daquv.agent.workflow.dto.UserInfo;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.function.Function;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/**
 * 체인 로그 컨텍스트 - 하나의 체인에 대한 모든 로그 정보
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ChainLogContext {

    private String chainId;
    private String userId;
    private String userQuestion;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private boolean completed;
    private boolean success;
    private List<ChainLogEntry> logEntries;

    // 메타데이터
    private String conversationId;
    private String companyId;
    private String selectedTable;
    private String sqlQuery;
    private String finalAnswer;
    private UserInfo userInfo; // 추가

    public ChainLogContext(String chainId, String userId, String userQuestion) {
        this.chainId = chainId;
        this.userId = userId;
        this.userQuestion = userQuestion;
        this.startTime = LocalDateTime.now();
        this.completed = false;
        this.success = false;
        this.logEntries = new CopyOnWriteArrayList<>();
    }

    /**
     * 로그 엔트리 추가
     */
    public void addLogEntry(ChainLogEntry entry) {
        logEntries.add(entry);
    }

    /**
     * 체인 완료 처리
     */
    public void complete(boolean success) {
        this.completed = true;
        this.success = success;
        this.endTime = LocalDateTime.now();
    }

    /**
     * 실행 시간 계산 (밀리초)
     */
    public long getDurationMs() {
        if (startTime == null) return 0;
        LocalDateTime end = endTime != null ? endTime : LocalDateTime.now();
        return java.time.Duration.between(startTime, end).toMillis();
    }

    /**
     * 특정 레벨의 로그 개수 조회
     */
    public long getLogCount(LogLevel level) {
        return logEntries.stream()
                .filter(entry -> entry.getLevel() == level)
                .count();
    }

    /**
     * 특정 노드의 로그 조회
     */
    public List<ChainLogEntry> getNodeLogs(String nodeId) {
        return logEntries.stream()
                .filter(entry -> nodeId.equals(entry.getNodeId()))
                .collect(Collectors.toList());
    }

    /**
     * 대화 ID 설정
     */
    public void setConversationId(String conversationId) {
        this.conversationId = conversationId;
    }

    /**
     * 회사 ID 설정
     */
    public void setCompanyId(String companyId) {
        this.companyId = companyId;
    }
    
    /**
     * 선택된 테이블 설정
     */
    public void setSelectedTable(String selectedTable) {
        this.selectedTable = selectedTable;
    }
    
    /**
     * SQL 쿼리 설정
     */
    public void setSqlQuery(String sqlQuery) {
        this.sqlQuery = sqlQuery;
    }
    
    /**
     * 최종 답변 설정
     */
    public void setFinalAnswer(String finalAnswer) {
        this.finalAnswer = finalAnswer;
    }
    
    /**
     * 사용자 정보 설정
     */
    public void setUserInfo(UserInfo userInfo) {
        this.userInfo = userInfo;
    }
}