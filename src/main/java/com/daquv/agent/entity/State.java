package com.daquv.agent.entity;

import com.daquv.agent.quvi.entity.BaseState;
import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;
import lombok.experimental.SuperBuilder;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.Table;

@Entity
@Table(name = "state")
@Getter
@Setter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@SuperBuilder
public class State extends BaseState {

    @Column(name = "table_pipe")
    private String tablePipe;

    @Column(name = "query_result", columnDefinition = "TEXT")
    private String queryResult;
}