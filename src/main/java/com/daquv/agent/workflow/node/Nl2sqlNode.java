package com.daquv.agent.workflow.node;

import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.quvi.llmadmin.QnaService;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.LlmOutputHandler;
import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import com.daquv.agent.workflow.util.LLMRequest;
import com.daquv.agent.quvi.util.WebSocketUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class Nl2sqlNode implements WorkflowNode {

    @Autowired
    private LLMRequest llmService;

    @Autowired
    private PromptBuilder promptBuilder;
    
    @Autowired
    private QnaService qnaService;

    @Autowired
    @Qualifier("promptJdbcTemplate")
    private JdbcTemplate promptJdbcTemplate;
    
    @Autowired
    private WebSocketUtils webSocketUtils;

    @Override
    public String getId() {
        return "nl2sql";
    }

    @Override
    public void execute(WorkflowState state) {
        String userQuestion = state.getUserQuestion();
        String selectedTable = state.getSelectedTable();
        String chainId = state.getChainId();

        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("사용자 질문이 없습니다.");
            state.setSqlError("사용자 질문이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다."));
            return;
        }

        if (selectedTable == null || selectedTable.trim().isEmpty()) {
            log.error("선택된 테이블이 없습니다.");
            state.setSqlError("선택된 테이블이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("TABLE_SELECTION_ERROR", "선택된 테이블이 없습니다."));
            return;
        }

        String schema = getSchema(selectedTable);
        if (schema == null) {
            log.error("테이블 스키마를 찾을 수 없습니다: {}", selectedTable);
            state.setSqlError("테이블 스키마를 찾을 수 없습니다: " + selectedTable);
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("TABLE_SELECTION_ERROR", "테이블 스키마를 찾을 수 없습니다: " + selectedTable));
            return;
        }
        
        // QnA ID 생성
        String qnaId = qnaService.createQnaId(state.getTraceId());
        
        // History 조회
        List<Map<String, Object>> nl2sqlHistory = promptBuilder.getNl2sqlHistory(chainId);
        
        // NL2SQL 프롬프트 생성 (few-shot + history 포함 + QnA 저장)
        PromptTemplate promptTemplate = promptBuilder.buildNL2SQLPromptWithFewShotsAndHistory(
            selectedTable, schema, userQuestion, nl2sqlHistory, qnaId);
        String prompt = promptTemplate.build();
        
        // LLM 호출
        String llmResponse = llmService.callNl2sql(prompt, qnaId, chainId);
        String sqlQuery = LlmOutputHandler.extractSqlQuery(llmResponse);

        if (sqlQuery == null || sqlQuery.trim().isEmpty()) {
            log.error("SQL 쿼리 생성에 실패했습니다.");
            state.setSqlError("SQL 쿼리 생성에 실패했습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("LLM_ERROR", "SQL 쿼리 생성에 실패했습니다."));
            return;
        }

        log.info("생성된 SQL 쿼리: {}", sqlQuery);
        state.setSqlQuery(sqlQuery);
        
        // WebSocket 메시지 전송
        Map<String, Object> data = new HashMap<>();
        data.put("sql_query", sqlQuery);
        webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "nl2sql", data);
    }

    private String getSchema(String tableName) {
        try {
            String query = "SELECT prompt FROM prompt_schema WHERE table_nm = ?";
            List<Map<String, Object>> results = promptJdbcTemplate.queryForList(query, tableName);

            if (results.isEmpty()) {
                log.warn("테이블 {}에 대한 스키마를 찾을 수 없습니다.", tableName);
                return null;
            }

            return (String) results.get(0).get("prompt");
        } catch (Exception e) {
            log.error("스키마 조회 중 오류 발생: {}", e.getMessage(), e);
            return null;
        }
    }
}