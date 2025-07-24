package com.daquv.agent.workflow.semanticquery;

public interface SemanticQueryWorkflowNode {
    void execute(SemanticQueryWorkflowState state);

    /**
     * 노드 ID 반환
     */
    String getId();
}
