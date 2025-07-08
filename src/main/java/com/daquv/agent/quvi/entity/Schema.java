package com.daquv.agent.quvi.entity;

import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import javax.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "prompt_schema")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Schema {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Long id;

    @Column(name = "table_nm", length = 255, nullable = false)
    private String tableNm;

    @Column(name = "prompt", columnDefinition = "TEXT")
    private String prompt;

    @CreationTimestamp
    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @Builder
    public Schema(String tableNm, String prompt) {
        this.tableNm = tableNm;
        this.prompt = prompt;
    }

    /**
     * 스키마 정보 업데이트
     */
    public void updateSchema(String tableNm, String prompt) {
        this.tableNm = tableNm;
        this.prompt = prompt;
    }

    /**
     * 프롬프트만 업데이트
     */
    public void updatePrompt(String prompt) {
        this.prompt = prompt;
    }
} 