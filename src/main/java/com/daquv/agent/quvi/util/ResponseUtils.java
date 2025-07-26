package com.daquv.agent.quvi.util;

import com.daquv.agent.quvi.workflow.WorkflowExecutionManagerService;
import java.util.*;

public class ResponseUtils {
    private ResponseUtils() {}

    public static Map<String, Object> buildResponse(
            WorkflowExecutionManagerService workflowExecutionManagerService,
            String sessionId,
            String workflowId,
            List<String> recommendList,
            long totalTime,
            String selectedWorkflow,
            Object requestProfiler, // 실제 타입은 RequestProfiler, 내부에서 캐스팅
            String message
    ) {
        Map<String, Object> response = new HashMap<>();
        response.put("status", 200);
        response.put("success", true);
        response.put("retCd", 200);
        response.put("message", message);

        Map<String, Object> body = new HashMap<>();
        String finalAnswer = workflowExecutionManagerService.extractFinalAnswer(selectedWorkflow, workflowId);
        if (finalAnswer == null || finalAnswer.trim().isEmpty()) {
            finalAnswer = "죄송합니다. 요청을 처리하는 중 오류가 발생했습니다.";
        }
        body.put("answer", finalAnswer);
        body.put("raw_data", workflowExecutionManagerService.extractQueryResult(selectedWorkflow, workflowId));
        body.put("session_id", sessionId);
        body.put("workflow_id", workflowId);
        body.put("recommend", recommendList);
        body.put("is_api", false);
        body.put("date_info", Arrays.asList(
                workflowExecutionManagerService.extractStartDate(selectedWorkflow, workflowId),
                workflowExecutionManagerService.extractEndDate(selectedWorkflow, workflowId)
        ));
        body.put("sql_query", workflowExecutionManagerService.extractSqlQuery(selectedWorkflow, workflowId));
        body.put("selected_table", workflowExecutionManagerService.extractSelectedTable(selectedWorkflow, workflowId));
        body.put("has_next", workflowExecutionManagerService.extractHasNext(selectedWorkflow, workflowId));
        body.put("workflow_status", "completed");
        body.put("hil_required", false);

        // 프로파일링 정보
        Map<String, Object> profile = new HashMap<>();
        if (workflowId != null && requestProfiler != null) {
            // 타입 안전하게 처리
            Map<String, Object> profileData = null;
            try {
                profileData = (Map<String, Object>) requestProfiler.getClass().getMethod("getProfile", String.class).invoke(requestProfiler, workflowId);
            } catch (Exception e) {
                // 무시: profileData는 null로 처리
            }
            if (profileData != null) {
                Map<String, Object> vectorDbDefault = new HashMap<>();
                vectorDbDefault.put("calls", 0);
                vectorDbDefault.put("total_time_ms", 0);
                vectorDbDefault.put("avg_time_ms", 0.0);
                profile.put("vector_db", profileData.getOrDefault("vector_db", vectorDbDefault));

                Map<String, Object> llmDefault = new HashMap<>();
                llmDefault.put("calls", 0);
                llmDefault.put("total_time_ms", 0);
                llmDefault.put("avg_time_ms", 0.0);
                profile.put("llm", profileData.getOrDefault("llm", llmDefault));

                Map<String, Object> dbNormalDefault = new HashMap<>();
                dbNormalDefault.put("calls", 0);
                dbNormalDefault.put("total_time_ms", 0);
                dbNormalDefault.put("avg_time_ms", 0.0);
                profile.put("db_normal", profileData.getOrDefault("db_main", dbNormalDefault));

                Map<String, Object> dbPromptDefault = new HashMap<>();
                dbPromptDefault.put("calls", 0);
                dbPromptDefault.put("total_time_ms", 0);
                dbPromptDefault.put("avg_time_ms", 0.0);
                profile.put("db_prompt", profileData.getOrDefault("db_prompt", dbPromptDefault));
            }
        }
        profile.put("total_time_ms", totalTime);
        body.put("profile", profile);

        response.put("body", body);
        return response;
    }
} 