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
@Table(name = "conversation")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Conversation implements Serializable {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Long id;

    @Column(name = "user_id", nullable = false)
    private String userId;

    @CreationTimestamp
    @Column(name = "conversation_start", nullable = false)
    private LocalDateTime conversationStart;

    @Column(name = "conversation_end")
    private LocalDateTime conversationEnd;

    @Enumerated(EnumType.STRING)
    @Column(name = "conversation_status")
    private ConversationStatus conversationStatus = ConversationStatus.active;

    @Column(name = "conversation_id", nullable = false, unique = true)
    private String conversationId;

    @OneToMany(mappedBy = "conversation", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<Chain> chains = new ArrayList<>();

    @Builder
    public Conversation(String userId, String conversationId) {
        this.userId = userId;
        this.conversationId = conversationId;
        this.conversationStatus = ConversationStatus.active;
    }

    /**
     * 대화 종료
     */
    public void endConversation() {
        this.conversationEnd = LocalDateTime.now();
        this.conversationStatus = ConversationStatus.completed;
    }

    /**
     * 대화 상태 변경
     */
    public void updateStatus(ConversationStatus status) {
        this.conversationStatus = status;
    }

    public enum ConversationStatus {
        active, completed, error
    }
    
    // 추가 메서드들
    public ConversationStatus getConversationStatus() {
        return conversationStatus;
    }
    
    public static Conversation create(String userId, String conversationId) {
        return new Conversation(userId, conversationId);
    }
} 