package com.daquv.agent.workflow.killjoy;

import com.daquv.agent.quvi.llmadmin.HistoryService;
import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.Arrays;
import java.util.List;
import java.util.Map;

@Component
public class KillJoyPromptBuilder {

    @Autowired
    private HistoryService historyService;

    @Autowired
    private PromptBuilder promptBuilder;

    public PromptTemplate buildKilljoyPromptWithHistory(String userQuestion, List<Map<String, Object>> killjoyHistory) {
        PromptTemplate template = PromptTemplate.fromFile("killjoy");
        String systemPrompt = template.replace("{user_question}", userQuestion);

        // 프롬프트 구성
        return PromptTemplate.from("")
                .withSystemPrompt(systemPrompt)
                .withHistory(killjoyHistory)
                .withUserMessage(userQuestion);
    }

    /**
     * Killjoy 노드용 history 조회 및 변환
     */
    public List<Map<String, Object>> getKilljoyHistory(String workflowId) {
        List<String> requiredFields = Arrays.asList("user_question", "final_answer");
        Map<String, List<Map<String, Object>>> historyDict = historyService.getHistory(workflowId, requiredFields, "killjoy", 5);
        return promptBuilder.convertToChatHistory(historyDict, requiredFields, "user_question", "final_answer");
    }
}
