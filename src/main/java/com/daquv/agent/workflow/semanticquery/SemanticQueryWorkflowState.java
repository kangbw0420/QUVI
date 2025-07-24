package com.daquv.agent.workflow.semanticquery;
import com.daquv.agent.workflow.dto.UserInfo;
import com.daquv.agent.workflow.dto.VectorNotes;
import lombok.*;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.WebSocketSession;

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
    private String selectedWorkflow;

    private String userQuestion;
    private String selectedTable;
    private String selectedApi;
    private String sqlQuery;
    private String sqlError;
    private List<Map<String, Object>> queryResult;
    private String fString;
    private String finalAnswer;
    private String tablePipe;
    private Integer totalRows;
    private String startDate;
    private String endDate;
    private String queryResultStatus;
    private List<String> queryResultList;
    private VectorNotes vectorNotes;

    @Builder.Default
    private Boolean isOpendue = false;
    @Builder.Default
    private Boolean noData = false;
    @Builder.Default
    private Boolean futureDate = false;
    @Builder.Default
    private Boolean invalidDate = false;
    @Builder.Default
    private Boolean queryChanged = false;
    @Builder.Default
    private Boolean hasNext = false;
    @Builder.Default
    private Boolean queryError = false;
    @Builder.Default
    private Integer safeCount = 0;
}
