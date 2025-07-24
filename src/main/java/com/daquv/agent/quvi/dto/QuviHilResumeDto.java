package com.daquv.agent.quvi.dto;

import lombok.Getter;
import lombok.Setter;
import lombok.ToString;

/**
 * HIL(Human-in-the-Loop) 워크플로우 재개 요청 DTO
 */
@Getter
@Setter
@ToString
public class QuviHilResumeDto {

    /**
     * 재개할 워크플로우 ID
     */
    private String workflowId;

    /**
     * 세션 ID
     */
    private String sessionId;

    /**
     * 사용자 입력 (날짜 명확화 등)
     */
    private String userInput;

    /**
     * 사용자 ID
     */
    private String userId;

    /**
     * 회사 ID
     */
    private String companyId;

    /**
     * HIL 타입 (date_clarification 등)
     */
    private String hilType;
}