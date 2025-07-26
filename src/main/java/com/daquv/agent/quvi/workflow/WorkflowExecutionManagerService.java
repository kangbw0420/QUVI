package com.daquv.agent.quvi.workflow;

import com.daquv.agent.quvi.dto.QuviRequestDto;
import com.daquv.agent.workflow.dto.UserInfo;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
@Slf4j
public class WorkflowExecutionManagerService { // 클래스 이름도 변경

    @Autowired
    private ApplicationContext applicationContext;

    private final Map<String, String> workflowServiceMapping = new HashMap<>();

    public WorkflowExecutionManagerService() {
        // 워크플로우 타입과 서비스 Bean 이름 매핑 (Bean 이름들도 변경됨)
        workflowServiceMapping.put("JOY", "joyWorkflowExecutionService");
        workflowServiceMapping.put("TOOLUSE", "toolUseWorkflowExecutionService");
        workflowServiceMapping.put("SEMANTICQUERY", "semanticQueryWorkflowExecutionService");
    }

    /**
     * 워크플로우별 State 생성 및 초기화
     */
    public Object createAndInitializeStateForWorkflow(String selectedWorkflow, QuviRequestDto request,
                                                      String sessionId, String workflowId) {
        WorkflowExecutionService workflowExecutionService = getWorkflowExecutionService(selectedWorkflow);
        return workflowExecutionService.createAndInitializeState(request, sessionId, workflowId);
    }

    /**
     * 워크플로우별 실행
     */
    public void executeSelectedWorkflow(String selectedWorkflow, String workflowId) {
        try {
            WorkflowExecutionService workflowExecutionService = getWorkflowExecutionService(selectedWorkflow);
            workflowExecutionService.executeWorkflow(workflowId);

            log.info("✅ {} 워크플로우 실행 완료", selectedWorkflow);

        } catch (Exception e) {
            log.error("❌ {} 워크플로우 실행 실패: {}", selectedWorkflow, e.getMessage(), e);
            throw e;
        }
    }

    /**
     * 워크플로우별 최종 State 조회
     */
    public Object getFinalStateForWorkflow(String selectedWorkflow, String workflowId) {
        WorkflowExecutionService workflowExecutionService = getWorkflowExecutionService(selectedWorkflow);
        return workflowExecutionService.getFinalState(workflowId);
    }

    /**
     * 워크플로우별 State 정리
     */
    public void cleanupStateForWorkflow(String selectedWorkflow, String workflowId) {
        try {
            WorkflowExecutionService workflowExecutionService = getWorkflowExecutionService(selectedWorkflow);
            workflowExecutionService.cleanupState(workflowId);
        } catch (Exception e) {
            log.warn("워크플로우 {} State 정리 실패 - workflowId: {}: {}", selectedWorkflow, workflowId, e.getMessage());
        }
    }

    /**
     * 모든 워크플로우 State 정리 (에러 시 사용)
     */
    public void cleanupAllStates(String workflowId) {
        for (String workflowType : workflowServiceMapping.keySet()) {
            try {
                cleanupStateForWorkflow(workflowType, workflowId);
            } catch (Exception e) {
                log.warn("{} State cleanup 실패: {}", workflowType, e.getMessage());
            }
        }
    }

    /**
     * State 객체에서 최종 답변 추출
     */
    public String extractFinalAnswer(String selectedWorkflow, String workflowId) {
        try {
            WorkflowExecutionService workflowExecutionService = getWorkflowExecutionService(selectedWorkflow);
            return workflowExecutionService.extractFinalAnswer(workflowId);
        } catch (Exception e) {
            log.error("최종 답변 추출 실패 - selectedWorkflow: {}, workflowId: {}", selectedWorkflow, workflowId, e);
            return "처리 중 오류가 발생했습니다.";
        }
    }

    /**
     * 워크플로우 서비스 인스턴스 획득
     */
    private WorkflowExecutionService getWorkflowExecutionService(String selectedWorkflow) {
        String serviceBeanName = workflowServiceMapping.get(selectedWorkflow);
        if (serviceBeanName == null) {
            throw new IllegalArgumentException("지원하지 않는 워크플로우 타입: " + selectedWorkflow);
        }

        try {
            return applicationContext.getBean(serviceBeanName, WorkflowExecutionService.class);
        } catch (Exception e) {
            log.error("워크플로우 실행 서비스 Bean 획득 실패: {}", serviceBeanName, e);
            throw new IllegalStateException("워크플로우 실행 서비스를 찾을 수 없습니다: " + selectedWorkflow);
        }
    }

    /**
     * State 객체에서 쿼리 결과 추출
     */
    public List<?> extractQueryResult(String selectedWorkflow, String workflowId) {
        try {
            WorkflowExecutionService workflowExecutionService = getWorkflowExecutionService(selectedWorkflow);
            return workflowExecutionService.extractQueryResult(workflowId);
        } catch (Exception e) {
            log.error("쿼리 결과 추출 실패 - selectedWorkflow: {}, workflowId: {}", selectedWorkflow, workflowId, e);
            return new ArrayList<>();
        }
    }

    /**
     * State 객체에서 시작 날짜 추출
     */
    public String extractStartDate(String selectedWorkflow, String workflowId) {
        try {
            WorkflowExecutionService workflowExecutionService = getWorkflowExecutionService(selectedWorkflow);
            return workflowExecutionService.extractStartDate(workflowId);
        } catch (Exception e) {
            log.error("시작 날짜 추출 실패 - selectedWorkflow: {}, workflowId: {}", selectedWorkflow, workflowId, e);
            return null;
        }
    }

    /**
     * State 객체에서 종료 날짜 추출
     */
    public String extractEndDate(String selectedWorkflow, String workflowId) {
        try {
            WorkflowExecutionService workflowExecutionService = getWorkflowExecutionService(selectedWorkflow);
            return workflowExecutionService.extractEndDate(workflowId);
        } catch (Exception e) {
            log.error("종료 날짜 추출 실패 - selectedWorkflow: {}, workflowId: {}", selectedWorkflow, workflowId, e);
            return null;
        }
    }

    /**
     * State 객체에서 SQL 쿼리 추출
     */
    public String extractSqlQuery(String selectedWorkflow, String workflowId) {
        try {
            WorkflowExecutionService workflowExecutionService = getWorkflowExecutionService(selectedWorkflow);
            return workflowExecutionService.extractSqlQuery(workflowId);
        } catch (Exception e) {
            log.error("SQL 쿼리 추출 실패 - selectedWorkflow: {}, workflowId: {}", selectedWorkflow, workflowId, e);
            return null;
        }
    }

    /**
     * State 객체에서 선택된 테이블/API 추출
     */
    public String extractSelectedTable(String selectedWorkflow, String workflowId) {
        try {
            WorkflowExecutionService workflowExecutionService = getWorkflowExecutionService(selectedWorkflow);
            return workflowExecutionService.extractSelectedTable(workflowId);
        } catch (Exception e) {
            log.error("선택된 테이블/API 추출 실패 - selectedWorkflow: {}, workflowId: {}", selectedWorkflow, workflowId, e);
            return null;
        }
    }

    /**
     * State 객체에서 UserInfo 추출
     */
    public UserInfo extractUserInfo(String selectedWorkflow, String workflowId, QuviRequestDto fallbackRequest) {
        try {
            // JOY 워크플로우는 UserInfo가 필요 없음
            if ("JOY".equals(selectedWorkflow)) {
                log.debug("JOY 워크플로우는 UserInfo가 필요하지 않습니다.");
                return null;
            }

            WorkflowExecutionService workflowExecutionService = getWorkflowExecutionService(selectedWorkflow);
            UserInfo userInfo = workflowExecutionService.extractUserInfo(workflowId);

            // JOY 워크플로우이거나 UserInfo가 null인 경우 fallback 사용
            if (userInfo == null && fallbackRequest != null) {
                return UserInfo.builder()
                        .userId(fallbackRequest.getUserId())
                        .companyId(fallbackRequest.getCompanyId())
                        .useInttId(fallbackRequest.getUseInttId())
                        .build();
            }

            return userInfo;
        } catch (Exception e) {
            log.error("UserInfo 추출 실패 - selectedWorkflow: {}, workflowId: {}", selectedWorkflow, workflowId, e);

            // 실패 시 fallback request에서 UserInfo 생성
            if (fallbackRequest != null) {
                return UserInfo.builder()
                        .userId(fallbackRequest.getUserId())
                        .companyId(fallbackRequest.getCompanyId())
                        .useInttId(fallbackRequest.getUseInttId())
                        .build();
            }
            return null;
        }
    }

    /**
     * State 객체에서 hasNext 플래그 추출
     */
    public Boolean extractHasNext(String selectedWorkflow, String workflowId) {
        try {
            WorkflowExecutionService workflowExecutionService = getWorkflowExecutionService(selectedWorkflow);
            return workflowExecutionService.extractHasNext(workflowId);
        } catch (Exception e) {
            log.error("hasNext 플래그 추출 실패 - selectedWorkflow: {}, workflowId: {}", selectedWorkflow, workflowId, e);
            return false;
        }
    }

    /**
     * 워크플로우가 HIL 대기 상태인지 확인 (기존 로직을 매니저로 이동)
     */
    public boolean isWorkflowWaitingForHil(String selectedWorkflow, String workflowId) {
        try {
            WorkflowExecutionService workflowExecutionService = getWorkflowExecutionService(selectedWorkflow);
            Object state = workflowExecutionService.getFinalState(workflowId);

            // 각 워크플로우별 HIL 상태 확인 로직
            switch (selectedWorkflow) {
                case "SEMANTICQUERY":
                    if (state instanceof com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState) {
                        com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState semanticState =
                                (com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState) state;
                        boolean hilRequired = semanticState.isHilRequired();
                        log.debug("SemanticQuery HIL 상태 확인 - workflowId: {}, hilRequired: {}", workflowId, hilRequired);
                        return hilRequired;
                    }
                    break;

                case "TOOLUSE":
                    // ToolUse에서 HIL이 필요한 경우의 로직 (향후 확장)
                    return false; // 현재는 HIL 미지원

                case "JOY":
                    // JOY에서 HIL이 필요한 경우의 로직 (향후 확장)
                    return false; // 현재는 HIL 미지원

                default:
                    log.warn("알 수 없는 워크플로우 타입: {}", selectedWorkflow);
                    return false;
            }

        } catch (Exception e) {
            log.error("HIL 상태 확인 중 오류 발생 - workflowId: {}", workflowId, e);
            return false;
        }

        return false;
    }

    /**
     * HIL 이후 워크플로우 재개
     */
    public void resumeWorkflowAfterHil(String selectedWorkflow, String workflowId, String userInput) {
        try {
            WorkflowExecutionService workflowExecutionService = getWorkflowExecutionService(selectedWorkflow);
            workflowExecutionService.resumeWorkflowAfterHil(workflowId, userInput);

            log.info("✅ {} 워크플로우 HIL 재개 완료 - workflowId: {}", selectedWorkflow, workflowId);

        } catch (UnsupportedOperationException e) {
            log.warn("⚠️ {} 워크플로우는 HIL 재개를 지원하지 않습니다 - workflowId: {}",
                    selectedWorkflow, workflowId);
            throw e;
        } catch (Exception e) {
            log.error("❌ {} 워크플로우 HIL 재개 실패 - workflowId: {}: {}",
                    selectedWorkflow, workflowId, e.getMessage(), e);
            throw e;
        }
    }

    /**
     * 워크플로우 타입 확인 (기존 QuviController의 determineWorkflowType 로직을 매니저로 이동)
     */
    public String determineWorkflowType(String workflowId) {
        // SemanticQuery State가 있는지 확인
        try {
            Object semanticState = getWorkflowExecutionService("SEMANTICQUERY").getFinalState(workflowId);
            if (semanticState != null) {
                return "SEMANTICQUERY";
            }
        } catch (Exception e) {
            log.debug("SEMANTICQUERY State 확인 중 예외: {}", e.getMessage());
        }

        // ToolUse State가 있는지 확인
        try {
            Object toolUseState = getWorkflowExecutionService("TOOLUSE").getFinalState(workflowId);
            if (toolUseState != null) {
                return "TOOLUSE";
            }
        } catch (Exception e) {
            log.debug("TOOLUSE State 확인 중 예외: {}", e.getMessage());
        }

        // JOY State가 있는지 확인
        try {
            Object joyState = getWorkflowExecutionService("JOY").getFinalState(workflowId);
            if (joyState != null) {
                return "JOY";
            }
        } catch (Exception e) {
            log.debug("JOY State 확인 중 예외: {}", e.getMessage());
        }

        throw new IllegalStateException("워크플로우 상태를 찾을 수 없습니다: " + workflowId);
    }

}