package com.daquv.agent.workflow.nl2sql;


public interface Nl2SqlWorkflowNode {
    void execute(Nl2SqlWorkflowState state);

    /**
     * 노드 ID 반환
     */
    String getId();
}
