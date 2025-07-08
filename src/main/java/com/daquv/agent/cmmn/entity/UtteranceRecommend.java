package com.daquv.agent.cmmn.entity;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Table;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@NoArgsConstructor
@Table(name = "utterance_recommend")
@Getter
@Builder
@AllArgsConstructor
public class UtteranceRecommend {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long seq;

    private String companyId;

    @Column(name = "utterance_contents", nullable = false, columnDefinition = "TEXT")
    private String utteranceContents;

    @Column(name = "order_by", columnDefinition = "int2")
    private Long orderBy;
}
