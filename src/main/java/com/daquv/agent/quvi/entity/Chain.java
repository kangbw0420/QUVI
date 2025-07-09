package com.daquv.agent.quvi.entity;

import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;

import javax.persistence.*;
import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "chain")
@Getter
@Setter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
public class Chain implements Serializable {

    @Id
    @Column(name = "id")
    private String id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "conversation_id", referencedColumnName = "conversation_id")
    private Conversation conversation;

    @Column(name = "chain_question", columnDefinition = "TEXT")
    private String chainQuestion;

    @Column(name = "chain_answer", columnDefinition = "TEXT")
    private String chainAnswer;

    @CreationTimestamp
    @Column(name = "chain_start", nullable = false)
    private LocalDateTime chainStart;

    @Column(name = "chain_end")
    private LocalDateTime chainEnd;

    @Enumerated(EnumType.STRING)
    @Column(name = "chain_status")
    private ChainStatus chainStatus = ChainStatus.active;

    @OneToMany(mappedBy = "chain", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<Trace> traces = new ArrayList<>();

    @Column(name = "chain_log", columnDefinition = "TEXT")
    private String chainLog;

    /**
     * 체인 완료
     */
    public void completeChain(String answer) {
        this.chainAnswer = answer;
        this.chainEnd = LocalDateTime.now();
        this.chainStatus = ChainStatus.completed;
    }

    /**
     * 체인 상태 변경
     */
    public void updateStatus(ChainStatus status) {
        this.chainStatus = status;
    }

    /**
     * 체인 지속 시간 계산 (초)
     */
    public Double getDurationSeconds() {
        if (chainEnd == null) {
            return 0.0;
        }
        return (double) java.time.Duration.between(chainStart, chainEnd).getSeconds();
    }

    public enum ChainStatus {
        active, completed, error
    }

    /**
     * 체인 로그 추가
     */
    public void addChainLog(String logEntry) {
        if (this.chainLog == null) {
            this.chainLog = logEntry;
        } else {
            this.chainLog += "\n" + logEntry;
        }
    }

    /**
     * 체인 에러 상태로 변경 및 로그 저장
     */
    public void markError(String errorMessage, String errorLog) {
        this.chainStatus = ChainStatus.error;
        this.chainEnd = LocalDateTime.now();
        this.chainAnswer = errorMessage;
        if (errorLog != null) {
            addChainLog(errorLog);
        }
    }

    public static Chain create(String id, Conversation conversation, String question, ChainStatus status) {
        Chain chain = new Chain();
        chain.id = id;
        chain.conversation = conversation;
        chain.chainQuestion = question;
        chain.chainStatus = status;
        return chain;
    }
} 