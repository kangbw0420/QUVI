package com.daquv.agent.quvi.util;

import com.daquv.agent.quvi.logging.WorkflowLogManager;
import com.daquv.agent.quvi.dto.LogLevel;
import org.slf4j.Logger;

import java.util.Map;

public class StatisticsUtils {
    private StatisticsUtils() {}

    public static void logNodeExecutionStatistics(Logger log, WorkflowLogManager chainLogManager, String workflowId, long totalTime, Map<String, Object> profileData, String logType) {
        try {
            log.info("📊 ===== 워크플로우 노드별 실행 통계 (Chain ID: {}) =====", workflowId);
            log.info("📊 전체 처리 시간: {}ms", totalTime);

            // 전체 타입별 요약 통계
            Map<String, Object> vectorDbStats = (Map<String, Object>) profileData.get("vector_db");
            Map<String, Object> llmStats = (Map<String, Object>) profileData.get("llm");
            Map<String, Object> dbMainStats = (Map<String, Object>) profileData.get("db_main");
            Map<String, Object> dbPromptStats = (Map<String, Object>) profileData.get("db_prompt");

            if (vectorDbStats != null) {
                int vectorCalls = (Integer) vectorDbStats.getOrDefault("calls", 0);
                long vectorTotalTime = (Long) vectorDbStats.getOrDefault("total_time_ms", 0L);
                double vectorAvgTime = (Double) vectorDbStats.getOrDefault("avg_time_ms", 0.0);
                log.info("📊 🔍 Vector DB 전체 - 호출횟수: {}회, 총 소요시간: {}ms, 평균 소요시간: {}ms", vectorCalls, vectorTotalTime, vectorAvgTime);
            }
            if (llmStats != null) {
                int llmCalls = (Integer) llmStats.getOrDefault("calls", 0);
                long llmTotalTime = (Long) llmStats.getOrDefault("total_time_ms", 0L);
                double llmAvgTime = (Double) llmStats.getOrDefault("avg_time_ms", 0.0);
                log.info("📊 🤖 LLM 전체 - 호출횟수: {}회, 총 소요시간: {}ms, 평균 소요시간: {}ms", llmCalls, llmTotalTime, llmAvgTime);
            }
            if (dbMainStats != null) {
                int dbMainCalls = (Integer) dbMainStats.getOrDefault("calls", 0);
                long dbMainTotalTime = (Long) dbMainStats.getOrDefault("total_time_ms", 0L);
                double dbMainAvgTime = (Double) dbMainStats.getOrDefault("avg_time_ms", 0.0);
                log.info("📊 🗄️ DB Main 전체 - 호출횟수: {}회, 총 소요시간: {}ms, 평균 소요시간: {}ms", dbMainCalls, dbMainTotalTime, dbMainAvgTime);
            }
            if (dbPromptStats != null) {
                int dbPromptCalls = (Integer) dbPromptStats.getOrDefault("calls", 0);
                long dbPromptTotalTime = (Long) dbPromptStats.getOrDefault("total_time_ms", 0L);
                double dbPromptAvgTime = (Double) dbPromptStats.getOrDefault("avg_time_ms", 0.0);
                log.info("📊 💾 DB Prompt 전체 - 호출횟수: {}회, 총 소요시간: {}ms, 평균 소요시간: {}ms", dbPromptCalls, dbPromptTotalTime, dbPromptAvgTime);
            }

            // 워크플로우 노드별 세분화된 통계
            Map<String, Object> workflowNodes = (Map<String, Object>) profileData.get("workflow_nodes");
            if (workflowNodes != null && !workflowNodes.isEmpty()) {
                log.info("📊 ===== 워크플로우 노드별 세분화 통계 =====");
                for (Map.Entry<String, Object> nodeEntry : workflowNodes.entrySet()) {
                    String nodeId = nodeEntry.getKey();
                    Map<String, Object> nodeData = (Map<String, Object>) nodeEntry.getValue();
                    int totalCalls = (Integer) nodeData.getOrDefault("total_calls", 0);
                    long totalTimeMs = (Long) nodeData.getOrDefault("total_time_ms", 0L);
                    double avgTime = (Double) nodeData.getOrDefault("avg_time_ms", 0.0);
                    log.info("📊 🔧 {} 노드 - 총 호출: {}회, 총 시간: {}ms, 평균: {}ms", nodeId, totalCalls, totalTimeMs, avgTime);
                    if (chainLogManager != null && logType != null) {
                        chainLogManager.addLog(workflowId, logType, LogLevel.INFO,
                                String.format("🔧 %s 노드 - 총 호출: %d회, 총 시간: %dms, 평균: %.2fms", nodeId, totalCalls, totalTimeMs, avgTime));
                    }
                    Map<String, Object> details = (Map<String, Object>) nodeData.get("details");
                    if (details != null && !details.isEmpty()) {
                        for (Map.Entry<String, Object> detailEntry : details.entrySet()) {
                            String type = detailEntry.getKey();
                            Map<String, Object> typeStats = (Map<String, Object>) detailEntry.getValue();
                            int typeCalls = (Integer) typeStats.getOrDefault("calls", 0);
                            long typeTime = (Long) typeStats.getOrDefault("total_time_ms", 0L);
                            double typeAvg = (Double) typeStats.getOrDefault("avg_time_ms", 0.0);
                            String typeIcon = getTypeIcon(type);
                            log.info("📊   └─ {} {}: {}회, {}ms, 평균 {}ms", typeIcon, type, typeCalls, typeTime, typeAvg);
                            if (chainLogManager != null && logType != null) {
                                chainLogManager.addLog(workflowId, logType, LogLevel.INFO,
                                        String.format("    └─ %s %s: %d회, %dms, 평균 %.2fms", typeIcon, type, typeCalls, typeTime, typeAvg));
                            }
                        }
                    }
                }
            }

            // 전체 요약
            int totalCalls = 0;
            long totalProfiledTime = 0L;
            if (vectorDbStats != null) {
                totalCalls += (Integer) vectorDbStats.getOrDefault("calls", 0);
                totalProfiledTime += (Long) vectorDbStats.getOrDefault("total_time_ms", 0L);
            }
            if (llmStats != null) {
                totalCalls += (Integer) llmStats.getOrDefault("calls", 0);
                totalProfiledTime += (Long) llmStats.getOrDefault("total_time_ms", 0L);
            }
            if (dbMainStats != null) {
                totalCalls += (Integer) dbMainStats.getOrDefault("calls", 0);
                totalProfiledTime += (Long) dbMainStats.getOrDefault("total_time_ms", 0L);
            }
            if (dbPromptStats != null) {
                totalCalls += (Integer) dbPromptStats.getOrDefault("calls", 0);
                totalProfiledTime += (Long) dbPromptStats.getOrDefault("total_time_ms", 0L);
            }
            double profiledPercentage = totalTime > 0 ? (double) totalProfiledTime / totalTime * 100 : 0.0;
            log.info("📊 ⭐ 전체 요약 - 총 노드 호출: {}회, 프로파일된 시간: {}ms ({}%), 기타 처리 시간: {}ms", totalCalls, totalProfiledTime, profiledPercentage, totalTime - totalProfiledTime);
            if (chainLogManager != null && logType != null) {
                chainLogManager.addLog(workflowId, logType, LogLevel.INFO,
                        String.format("⭐ 전체 요약 - 총 노드 호출: %d회, 프로파일된 시간: %dms (%.1f%%), 기타 처리 시간: %dms", totalCalls, totalProfiledTime, profiledPercentage, totalTime - totalProfiledTime));
            }
            log.info("📊 ===== 통계 종료 =====");
        } catch (Exception e) {
            log.warn("📊 워크플로우 노드별 실행 통계 로깅 중 오류 발생: {}", e.getMessage(), e);
        }
    }

    public static String getTypeIcon(String type) {
        switch (type) {
            case "vector_db":
                return "🔍";
            case "llm":
                return "🤖";
            case "db_main":
                return "🗄️";
            case "db_prompt":
                return "💾";
            default:
                return "❓";
        }
    }
} 