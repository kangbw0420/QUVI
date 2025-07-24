package com.daquv.agent.workflow.tooluse;


public interface ToolUseWorkflowNode {
    void execute(ToolUseWorkflowState state);

    /**
     * 노드 ID 반환
     */
    String getId();
}
