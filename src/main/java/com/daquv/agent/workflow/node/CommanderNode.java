package com.daquv.agent.workflow.node;

import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.quvi.llmadmin.GenerationService;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.LlmOutputHandler;
import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptBuilder.PromptWithRetrieveTime;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import com.daquv.agent.workflow.util.LLMRequest;
import com.daquv.agent.quvi.util.WebSocketUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class CommanderNode implements WorkflowNode {

    @Autowired
    private LLMRequest llmService;

    @Autowired
    private PromptBuilder promptBuilder;
    
    @Autowired
    private GenerationService generationService;
    
    @Autowired
    private WebSocketUtils webSocketUtils;

    @Autowired
    private RequestProfiler requestProfiler;

    @Override
    public String getId() {
        return "commander";
    }

    @Override
    public void execute(WorkflowState state) {
        String userQuestion = state.getUserQuestion();
        String chainId = state.getWorkflowId();

        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("사용자 질문이 없습니다.");
            state.setSqlError("사용자 질문이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다."));
            return;
        }

        // QnA ID 생성
        String qnaId = generationService.createQnaId(state.getNodeId());
        
        // History 조회 (Commander는 history를 사용하지 않지만 일관성을 위해 추가)
        List<Map<String, Object>> commanderHistory = promptBuilder.getHistory(chainId,
            Arrays.asList("user_question", "selected_table"), "commander", 5);
        
        // Commander 프롬프트 생성 (few-shot 포함 + QnA 저장)
        PromptWithRetrieveTime promptResult = promptBuilder.buildCommanderPromptWithFewShots(userQuestion, qnaId, chainId);
        PromptTemplate promptTemplate = promptResult.getPromptTemplate();
        BigDecimal retrieveTime = promptResult.getRetrieveTime();

        String prompt = promptTemplate.build();
        
        // LLM 호출하여 테이블 선택
        long startTime = System.currentTimeMillis();
        String llmResponse = llmService.callSelector(prompt, qnaId, chainId);
        long endTime = System.currentTimeMillis();

        double elapsedTime = (endTime - startTime) / 1000.0;
        requestProfiler.recordLlmCall(chainId, elapsedTime, "commander");
        String selectedTable = LlmOutputHandler.extractTableName(llmResponse);

        if (selectedTable == null || selectedTable.trim().isEmpty()) {
            log.error("테이블 선택에 실패했습니다.");
            state.setSqlError("테이블 선택에 실패했습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("TABLE_SELECTION_ERROR", "테이블 선택에 실패했습니다."));
            return;
        }

        log.info("선택된 테이블: {}", selectedTable);
        state.setSelectedTable(selectedTable);

        generationService.recordAnswer(qnaId, selectedTable, retrieveTime);
        
        // WebSocket 메시지 전송
        Map<String, Object> data = new HashMap<>();
        data.put("selected_table", selectedTable);
        webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "commander", data);
    }
} 