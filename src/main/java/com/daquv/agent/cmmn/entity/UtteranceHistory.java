package com.daquv.agent.cmmn.entity;

import java.time.LocalDateTime;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Table;

import org.hibernate.annotations.CreationTimestamp;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@NoArgsConstructor
@Table(name = "utterance_history")
@Getter
@Builder
@AllArgsConstructor
public class UtteranceHistory {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long seq;

    private String userId;

    private String companyId;

    @CreationTimestamp
    @Column(name = "utterance_date", nullable = false, updatable = false)
    private LocalDateTime utteranceDate;

    @Column(name = "utterance_contents", columnDefinition = "TEXT")
    private String utteranceContents;
}
