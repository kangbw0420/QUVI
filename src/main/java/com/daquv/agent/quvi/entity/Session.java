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
    private LocalDateTime conversationStart;

    @Column(name = "session_end")
    private LocalDateTime conversationEnd;

    @Enumerated(EnumType.STRING)
    @Column(name = "session_status")
    private SessionStatus conversationStatus = SessionStatus.active;

    @OneToMany(mappedBy = "session", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<Workflow> workflows = new ArrayList<>();

    @Builder
    public Session(String userId, String sessionId, String companyId) {
        this.userId = userId;
        this.sessionId = sessionId;
        this.companyId = companyId;
        this.conversationStatus = SessionStatus.active;
    }

    /**
     * 대화 종료
     */
    public void endConversation() {
        this.conversationEnd = LocalDateTime.now();
        this.conversationStatus = SessionStatus.completed;
    }

    /**
     * 대화 상태 변경
     */
    public void updateStatus(SessionStatus status) {
        this.conversationStatus = status;
    }

    public enum SessionStatus {
        active, completed, error
    }
    
    // 추가 메서드들
    public SessionStatus getConversationStatus() {
        return conversationStatus;
    }
    
    public static Session create(String userId, String conversationId, String companyId) {
        return new Session(userId, conversationId, companyId);
    }
} 