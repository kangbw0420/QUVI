package com.daquv.agent.quvi.entity;

import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import javax.persistence.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "qna")
@Getter
@Setter
@NoArgsConstructor(access = AccessLevel.PUBLIC)
@AllArgsConstructor
@Builder
public class Qna {

    @Id
    @Column(name = "id")
    private String id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "trace_id")
    private Trace trace;

    @Column(name = "question", columnDefinition = "TEXT")
    private String question;

    @Column(name = "answer", columnDefinition = "TEXT")
    private String answer;

    @Column(name = "model")
    private String model;

    @CreationTimestamp
    @Column(name = "question_timestamp", nullable = false)
    private LocalDateTime questionTimestamp;

    @UpdateTimestamp
    @Column(name = "answer_timestamp")
    private LocalDateTime answerTimestamp;

    @Column(name = "retrieve_time", precision = 8, scale = 6)
    private BigDecimal retrieveTime;

    @OneToMany(mappedBy = "qna", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<Fewshot> fewshots = new ArrayList<>();

    /**
     * 답변 설정
     */
    public void setAnswer(String answer) {
        this.answer = answer;
        this.answerTimestamp = LocalDateTime.now();
    }

    /**
     * 검색 시간 설정
     */
    public void setRetrieveTime(BigDecimal retrieveTime) {
        this.retrieveTime = retrieveTime;
    }

    /**
     * 모델 설정
     */
    public void setModel(String model) {
        this.model = model;
    }
} 