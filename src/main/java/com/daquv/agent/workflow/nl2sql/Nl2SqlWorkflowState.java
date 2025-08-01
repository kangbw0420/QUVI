package com.daquv.agent.workflow.nl2sql;

import com.daquv.agent.workflow.dto.UserInfo;
import com.daquv.agent.workflow.dto.VectorNotes;
import lombok.Builder;
import lombok.Data;
import org.springframework.web.socket.WebSocketSession;

import java.util.List;
import java.util.Map;

@Data
@Builder
public class Nl2SqlWorkflowState {
    private String workflowId;
    private String nodeId;
    private UserInfo userInfo;
    private WebSocketSession webSocketSession;
    private String userQuestion;
    private String selectedTable;

    private String sqlQuery;
    private String sqlError;
    private List<String> columnList;

    private List<Map<String, Object>> queryResult;
    private Integer totalRows;
    private VectorNotes vectorNotes;
    private String queryResultStatus;
    private List<String> queryResultList;

    private String fString;
    private String finalAnswer;

    private String tablePipe;
    private String startDate;
    private String endDate;

    private Boolean dateClarificationNeeded = false; // 날짜 명확화가 필요한지 여부

    private String currentNode; // HIL이 발생한 현재 노드


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
