package com.daquv.agent.quvi.entity;

import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import javax.persistence.*;
import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "session")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Session implements Serializable {

    @Id
    @Column(name = "session_id")
    private String sessionId;

    @Column(name = "user_id", nullable = false)
    private String userId;

    @Column(name = "company_id")
    private String companyId;

    @CreationTimestamp
    @Column(name = "session_start", nullable = false)
    private LocalDateTime sessionStart;

    @Column(name = "session_end")
    private LocalDateTime sessionEnd;

    @Enumerated(EnumType.STRING)
    @Column(name = "session_status")
    private SessionStatus sessionStatus = SessionStatus.active;

    @OneToMany(mappedBy = "session", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<Workflow> workflows = new ArrayList<>();

    @Builder
    public Session(String userId, String sessionId, String companyId) {
        this.userId = userId;
        this.sessionId = sessionId;
        this.companyId = companyId;
        this.sessionStart = LocalDateTime.now();
        this.sessionStatus = SessionStatus.active;
    }

    /**
     * 대화 종료
     */
    public void endConversation() {
        this.sessionEnd = LocalDateTime.now();
        this.sessionStatus = SessionStatus.completed;
    }

    /**
     * 대화 상태 변경
     */
    public void updateStatus(SessionStatus status) {
        this.sessionStatus = status;
    }

    public enum SessionStatus {
        active, completed, error
    }
    
    // 추가 메서드들
    public SessionStatus getSessionStatus() {
        return sessionStatus;
    }
    
    public static Session create(String userId, String sessionId, String companyId) {
        return new Session(userId, sessionId, companyId);
    }
} 