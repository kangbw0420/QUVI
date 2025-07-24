package com.daquv.agent.workflow.semanticquery;
import com.daquv.agent.workflow.dto.UserInfo;
import com.daquv.agent.workflow.dto.VectorNotes;
import lombok.*;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.WebSocketSession;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Component
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@ToString
public class SemanticQueryWorkflowState {
    private String workflowId;
    private String nodeId;
    private UserInfo userInfo;
    private WebSocketSession webSocketSession;
    private String userQuestion;
    private Map<String, SemanticQueryExecution> semanticQueryExecutionMap;
    private String finalAnswer;
    private String selectedTable;

    private String startDate;
    private String endDate;

    private Boolean dateClarificationNeeded = false; // 날짜 명확화가 필요한지 여부

    private String currentNode; // HIL이 발생한 현재 노드

    @Data
    @Builder
    public static class SemanticQueryExecution {
        private Map<String, String> sqlQuery;
        private String sqlError;

        private Map<String, Object> queryResult;
        private List<Map<String, Object>> postQueryResult;
        private Map<String, Integer> totalRows;
        private VectorNotes vectorNotes;
        @Builder.Default
        private Map<String, DSL> dsl = new HashMap<>();
        private String queryResultStatus;
        private List<String> queryResultList;

        private String fString;
        private String finalAnswer;

        private String tablePipe;
        private String startDate;
        private String endDate;


        @Builder.Default
        private Boolean noData = false;
        @Builder.Default
        private Boolean futureDate = false;
        @Builder.Default
        private Boolean invalidDate = false;
        @Builder.Default
        private Boolean queryError = false;
        @Builder.Default
        private Boolean queryChanged = false;
        @Builder.Default
        private Boolean hasNext = false;
        @Builder.Default
        private Integer safeCount = 0;
        @Builder.Default
        private Boolean noteChanged = false;

        public void incrementSafeCount() {
            this.safeCount = (this.safeCount != null ? this.safeCount : 0) + 1;
        }

        public void addQueryResult(String key, Object value) {
            if (this.queryResult == null) {
                this.queryResult = new HashMap<>();
            }
            this.queryResult.put(key, value);
        }

        public void addSqlQuery(String key, String query) {
            if (this.sqlQuery == null) {
                this.sqlQuery = new HashMap<>();
            }
            this.sqlQuery.put(key, query);
        }

        public void addTotalRows(String key, Integer rows) {
            if (this.totalRows == null) {
                this.totalRows = new HashMap<>();
            }
            this.totalRows.put(key, rows);
        }
    }

    @Data
    public static class DSL {
        private List<String> metrics = new ArrayList<>();
        private List<String> groupBy = new ArrayList<>();
        private List<String> filters = new ArrayList<>();
        private List<String> orderBy = new ArrayList<>();
        private Integer limit;
    }

    /**
     * HIL 상태 확인
     */
    public boolean isHilRequired() {
        return dateClarificationNeeded != null && dateClarificationNeeded;
    }

    /**
     * HIL 상태 초기화
     */
    public void clearHilState() {
        this.dateClarificationNeeded = false;
        this.currentNode = null;
    }

    /**
     * 날짜 정보가 설정되었는지 확인
     */
    public boolean hasDateInfo() {
        return startDate != null && !startDate.trim().isEmpty() &&
                endDate != null && !endDate.trim().isEmpty();
    }
}