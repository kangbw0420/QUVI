package com.daquv.agent.workflow;

/**
 * State를 직접 받는 워크플로우 노드 인터페이스
 */
public interface WorkflowNode {
    /**
     * State를 직접 받아서 노드 실행
     */
    void execute(WorkflowState state);
    
    /**
     * 노드 ID 반환
     */
    String getId();
} 