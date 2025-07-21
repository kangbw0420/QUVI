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
@Table(name = "generation")
@Getter
@Setter
@NoArgsConstructor(access = AccessLevel.PUBLIC)
@AllArgsConstructor
@Builder
public class Generation {

    @Id
    @Column(name = "id")
    private String id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "node_id")
    private Node node;

    @Column(name = "prompt", columnDefinition = "TEXT")
    private String prompt;

    @Column(name = "output", columnDefinition = "TEXT")
    private String output;

    @Column(name = "model")
    private String model;

    @CreationTimestamp
    @Column(name = "generation_start", nullable = false)
    private LocalDateTime questionTimestamp;

    @UpdateTimestamp
    @Column(name = "generation_end")
    private LocalDateTime answerTimestamp;

    @Column(name = "token_usage", columnDefinition = "TEXT")
    private String retrieveTime;

//    @OneToMany(mappedBy = "generation", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
//    private List<Fewshot> fewshots = new ArrayList<>();

    /**
     * 답변 설정
     */
    public void setAnswer(String answer) {
        this.output = answer;
        this.answerTimestamp = LocalDateTime.now();
    }

//    /**
//     * 검색 시간 설정
//     */
//    public void setRetrieveTime(BigDecimal retrieveTime) {
//        this.retrieveTime = retrieveTime;
//    }

    /**
     * 모델 설정
     */
    public void setModel(String model) {
        this.model = model;
    }
} 