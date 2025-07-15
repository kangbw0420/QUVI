package com.daquv.agent.workflow.node;

import com.daquv.agent.quvi.llmadmin.QnaService;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.LlmOutputHandler;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.util.WebSocketUtils;
import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptBuilder.PromptWithRetrieveTime;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import com.daquv.agent.workflow.util.LLMRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
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
    private WebSocketUtils webSocketUtils;

    @Autowired
    private RequestProfiler requestProfiler;

    @Override
    public String getId() {
        return "nl2sql";
    }

    @Override
    public void execute(WorkflowState state) {
        String userQuestion = state.getUserQuestion();
        String selectedTable = state.getSelectedTable();
        String chainId = state.getChainId();
        String companyId = state.getUserInfo().getCompanyId();
        String startDate = state.getStartDate();
        String endDate = state.getEndDate();

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
        
        // QnA ID 생성
        String qnaId = qnaService.createQnaId(state.getTraceId());
        
        // History 조회
        List<Map<String, Object>> nl2sqlHistory = promptBuilder.getNl2sqlHistory(chainId);
        
        // NL2SQL 프롬프트 생성 (few-shot + history 포함 + QnA 저장)
        PromptWithRetrieveTime promptResult = promptBuilder.buildNL2SQLPromptWithFewShotsAndHistory(
            selectedTable, userQuestion, nl2sqlHistory, qnaId, companyId, startDate, endDate, chainId);
        PromptTemplate promptTemplate = promptResult.getPromptTemplate();
        BigDecimal retrieveTime = promptResult.getRetrieveTime();
        String prompt = promptTemplate.build();
        
        // LLM 호출
        long startTime = System.currentTimeMillis();
        String llmResponse = llmService.callNl2sql(prompt, qnaId, chainId);
        long endTime = System.currentTimeMillis();

        // LLM 프로파일링 기록
        double elapsedTime = (endTime - startTime) / 1000.0;
        requestProfiler.recordLlmCall(chainId, elapsedTime, "nl2sql");
        llmResponse = LlmOutputHandler.handleAiColon(llmResponse);
        String sqlQuery = LlmOutputHandler.extractSqlQuery(llmResponse);

        if (sqlQuery == null || sqlQuery.trim().isEmpty()) {
            log.error("SQL 쿼리 생성에 실패했습니다.");
            state.setSqlError("SQL 쿼리 생성에 실패했습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("LLM_ERROR", "SQL 쿼리 생성에 실패했습니다."));
            return;
        }

        log.info("생성된 SQL 쿼리: {}", sqlQuery);
        state.setSqlQuery(sqlQuery);

        qnaService.recordAnswer(qnaId, sqlQuery, retrieveTime);
        
        // WebSocket 메시지 전송
        Map<String, Object> data = new HashMap<>();
        data.put("sql_query", sqlQuery);
        webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "nl2sql", data);
    }
}