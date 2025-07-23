package com.daquv.agent.quvi.entity;

import com.daquv.agent.entity.State;
import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.Type;

import javax.persistence.*;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "node")
@Getter
@Setter
@NoArgsConstructor(access = AccessLevel.PUBLIC)
@AllArgsConstructor
@Builder
public class Node {

    @Id
    @Column(name = "node_id")
    private String nodeId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "workflow_id")
    private Workflow workflow;

    @Type(type = "com.vladmihalcea.hibernate.type.json.JsonBinaryType")
    @Column(name = "node_state_json", columnDefinition = "jsonb")
    private String nodeStateJson;

    @Column(name = "node_start")
    private LocalDateTime nodeStart;

    @Column(name = "node_end")
    private LocalDateTime nodeEnd;

    @Column(name = "node_name")
    private String nodeName;

    @Enumerated(EnumType.STRING)
    @Column(name = "node_status")
    private NodeStatus nodeStatus = NodeStatus.active;

    @OneToMany(mappedBy = "node", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<State> states = new ArrayList<>();

    @OneToMany(mappedBy = "node", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<Generation> generations = new ArrayList<>();

    /**
     * 트레이스 완료
     */
    public void completeTrace() {
        this.nodeEnd = LocalDateTime.now();
        this.nodeStatus = NodeStatus.completed;
    }

    /**
     * 트레이스 상태 변경
     */
    public void updateStatus(NodeStatus status) {
        this.nodeStatus = status;
    }

//    /**
//     * 트레이스 지속 시간 계산 (초)
//     */
//    public Double getDurationSeconds() {
//        if (nodeEnd == null) {
//            return 0.0;
//        }
//        return (double) java.time.Duration.between(nodeStart, nodeEnd).getSeconds();
//    }

    /**
     * 노드 상태를 JSON으로 설정
     */
    public void setNodeStateAsJson(String stateJson) {
        this.nodeStateJson = stateJson;
    }

    public enum NodeStatus {
        active, completed, error
    }
} 