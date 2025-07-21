//package com.daquv.agent.quvi.entity;
//
//import lombok.AccessLevel;
//import lombok.AllArgsConstructor;
//import lombok.Builder;
//import lombok.Getter;
//import lombok.NoArgsConstructor;
//import lombok.Setter;
//import org.hibernate.annotations.CreationTimestamp;
//
//import javax.persistence.*;
//import java.time.LocalDateTime;
//
//@Entity
//@Table(name = "fewshot")
//@Getter
//@Setter
//@NoArgsConstructor(access = AccessLevel.PUBLIC)
//@AllArgsConstructor
//@Builder
//public class Fewshot {
//
//    @Id
//    @Column(name = "id")
//    private String id;
//
//    @ManyToOne(fetch = FetchType.LAZY)
//    @JoinColumn(name = "generation_id", nullable = false, referencedColumnName = "id")
//    private Generation generation;
//
//    @Column(name = "fewshot_human", columnDefinition = "TEXT")
//    private String fewshotHuman;
//
//    @Column(name = "fewshot_ai", columnDefinition = "TEXT")
//    private String fewshotAi;
//
//    @Column(name = "order_seq", nullable = false)
//    private Integer orderSeq;
//
//    @CreationTimestamp
//    @Column(name = "created_at", nullable = false)
//    private LocalDateTime createdAt;
//
//    @Column(name = "fewshot_retrieved", columnDefinition = "TEXT")
//    private String fewshotRetrieved;
//
//    /**
//     * Fewshot 정보 업데이트
//     */
//    public void updateFewshot(String fewshotHuman, String fewshotAi, String fewshotRetrieved) {
//        this.fewshotHuman = fewshotHuman;
//        this.fewshotAi = fewshotAi;
//        this.fewshotRetrieved = fewshotRetrieved;
//    }
//
//    /**
//     * 순서 변경
//     */
//    public void updateOrderSeq(Integer orderSeq) {
//        this.orderSeq = orderSeq;
//    }
//}