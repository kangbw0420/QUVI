package com.daquv.agent.quvi.entity;

import com.daquv.agent.entity.State;
import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;

import javax.persistence.*;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "trace")
@Getter
@Setter
@NoArgsConstructor(access = AccessLevel.PUBLIC)
@AllArgsConstructor
@Builder
public class Trace {

    @Id
    @Column(name = "id")
    private String id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "chain_id")
    private Chain chain;

    @Column(name = "node_type")
    private String nodeType;

    @CreationTimestamp
    @Column(name = "trace_start", nullable = false)
    private LocalDateTime traceStart;

    @Column(name = "trace_end")
    private LocalDateTime traceEnd;

    @Enumerated(EnumType.STRING)
    @Column(name = "trace_status")
    private TraceStatus traceStatus = TraceStatus.active;

    @OneToMany(mappedBy = "trace", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<State> states = new ArrayList<>();

    @OneToMany(mappedBy = "trace", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<Qna> qnas = new ArrayList<>();

    /**
     * 트레이스 완료
     */
    public void completeTrace() {
        this.traceEnd = LocalDateTime.now();
        this.traceStatus = TraceStatus.completed;
    }

    /**
     * 트레이스 상태 변경
     */
    public void updateStatus(TraceStatus status) {
        this.traceStatus = status;
    }

    /**
     * 트레이스 지속 시간 계산 (초)
     */
    public Double getDurationSeconds() {
        if (traceEnd == null) {
            return 0.0;
        }
        return (double) java.time.Duration.between(traceStart, traceEnd).getSeconds();
    }

    public enum TraceStatus {
        active, completed, error
    }
} 