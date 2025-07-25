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
@Table(name = "workflow")
@Getter
@Setter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
public class Workflow implements Serializable {

    @Id
    @Column(name = "workflow_id")
    private String workflowId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "session_id", referencedColumnName = "session_id")
    private Session session;

    @CreationTimestamp
    @Column(name = "workflow_start", nullable = false)
    private LocalDateTime workflowStart;

    @Column(name = "workflow_end")
    private LocalDateTime workflowEnd;

    @Enumerated(EnumType.STRING)
    @Column(name = "workflow_status")
    private WorkflowStatus workflowStatus = WorkflowStatus.active;

    @Column(name = "workflow_question", columnDefinition = "TEXT")
    private String workflowQuestion;

    @Column(name = "workflow_answer", columnDefinition = "TEXT")
    private String workflowAnswer;

    @Column(name = "workflow_log", columnDefinition = "TEXT")
    private String workflowLog;

    @OneToMany(mappedBy = "workflow", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<Node> nodes = new ArrayList<>();

    /**
     * 체인 완료
     */
    public void completeChain(String answer) {
        this.workflowEnd = LocalDateTime.now();
        this.workflowAnswer = answer;
        this.workflowStatus = WorkflowStatus.completed;
    }

    public void waitingWorkflow(String answer) {
        this.workflowAnswer = answer;
        this.workflowEnd = LocalDateTime.now();
        this.workflowStatus = WorkflowStatus.waiting;
    }

    /**
     * 체인 상태 변경
     */
    public void updateStatus(WorkflowStatus status) {
        this.workflowStatus = status;
    }

//    /**
//     * 체인 지속 시간 계산 (초)
//     */
//    public Double getDurationSeconds() {
//        if (workflowEnd == null) {
//            return 0.0;
//        }
//        return (double) java.time.Duration.between(workflowStatus, workflowEnd).getSeconds();
//    }

    public enum WorkflowStatus {
        active, completed, error, waiting
    }

//    /**
//     * 체인 로그 추가
//     */
//    public void addChainLog(String logEntry) {
//        if (this.chainLog == null) {
//            this.chainLog = logEntry;
//        } else {
//            this.chainLog += "\n" + logEntry;
//        }
//    }

    /**
     * 체인 에러 상태로 변경 및 로그 저장
     */
    public void markError(String errorMessage, String errorLog) {
        this.workflowStatus = WorkflowStatus.error;
        this.workflowEnd = LocalDateTime.now();
    }

    public static Workflow create(String workflowId, Session session, String question, WorkflowStatus status) {
        Workflow workflow = new Workflow();
        workflow.workflowId = workflowId;
        workflow.workflowQuestion = question;
        workflow.session = session;
        workflow.workflowStatus = status;
        return workflow;
    }
} 