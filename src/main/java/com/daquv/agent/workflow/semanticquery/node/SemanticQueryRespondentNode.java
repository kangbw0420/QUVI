package com.daquv.agent.workflow.semanticquery.node;

import com.daquv.agent.quvi.llmadmin.GenerationService;
import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.LlmOutputHandler;
import com.daquv.agent.quvi.util.WebSocketUtils;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowNode;
import com.daquv.agent.workflow.semanticquery.SemanticQueryWorkflowState;
import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptBuilder.PromptWithRetrieveTime;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import com.daquv.agent.quvi.requests.FstringRequest;
import com.daquv.agent.workflow.util.LLMRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.*;

@Component("semanticQueryRespondentNode")
@Slf4j
public class SemanticQueryRespondentNode implements SemanticQueryWorkflowNode {

    @Autowired
    private LLMRequest llmService;

    @Autowired
    private PromptBuilder promptBuilder;

    @Autowired
    private GenerationService qnaService;

    private final FstringRequest fstringRequest;

    @Autowired
    private WebSocketUtils webSocketUtils;

    @Autowired
    private RequestProfiler requestProfiler;

    public SemanticQueryRespondentNode(FstringRequest fstringRequest) {
        this.fstringRequest = fstringRequest;
    }

    @Override
    public String getId() {
        return "semanticQueryRespondent";
    }

    @Override
    public void execute(SemanticQueryWorkflowState state) {
        String userQuestion = state.getUserQuestion();
        String workflowId = state.getWorkflowId();

        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("사용자 질문이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다."));
            return;
        }

        Map<String, SemanticQueryWorkflowState.SemanticQueryExecution> executionMap = state.getSemanticQueryExecutionMap();
        if (executionMap == null || executionMap.isEmpty()) {
            log.error("SemanticQueryExecution이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("NO_DATA", "처리할 데이터가 없습니다."));
            return;
        }

        log.info("=== SemanticQueryRespondentNode 실행 시작 ===");
        log.info("사용자 질문: {}", userQuestion);
        log.info("처리할 Entity 수: {}", executionMap.size());

        try {
            // 모든 execution에서 결과 데이터 수집
            List<Map<String, Object>> allQueryResults = new ArrayList<>();
            List<Map<String, Object>> allPostProcessResults = new ArrayList<>();
            StringBuilder combinedTablePipe = new StringBuilder();
            boolean hasValidResults = false;
            boolean hasPostProcessResults = false;

            for (Map.Entry<String, SemanticQueryWorkflowState.SemanticQueryExecution> entry : executionMap.entrySet()) {
                String entity = entry.getKey();
                SemanticQueryWorkflowState.SemanticQueryExecution execution = entry.getValue();

                log.debug("Entity '{}' 결과 처리 중", entity);

                // 쿼리 결과 수집
                if (execution.getQueryResult() != null && !execution.getQueryResult().isEmpty()) {
                    for (Object result : execution.getQueryResult().values()) {
                        if (result instanceof List) {
                            List<Map<String, Object>> queryResult = (List<Map<String, Object>>) result;
                            allQueryResults.addAll(queryResult);
                            hasValidResults = true;
                        }
                    }
                }

                // 후처리 결과 수집
                if (execution.getPostQueryResult() != null && !execution.getPostQueryResult().isEmpty()) {
                    allPostProcessResults.addAll(execution.getPostQueryResult());
                    hasPostProcessResults = true;
                }

                // TablePipe 수집
                if (execution.getTablePipe() != null && !execution.getTablePipe().trim().isEmpty()) {
                    if (combinedTablePipe.length() > 0) {
                        combinedTablePipe.append("\n\n--- ").append(entity.toUpperCase()).append(" ---\n");
                    }
                    combinedTablePipe.append(execution.getTablePipe());
                }
            }

            if (!hasValidResults && !hasPostProcessResults) {
                log.warn("모든 execution에서 유효한 결과가 없습니다.");
                state.setFinalAnswer("요청하신 조건에 해당하는 데이터가 없습니다.");
                return;
            }

            // 우선순위: PostProcess 결과 > 원본 쿼리 결과
            List<Map<String, Object>> finalResults = hasPostProcessResults ? allPostProcessResults : allQueryResults;
            String tablePipeForPrompt = combinedTablePipe.toString();

            log.info("최종 사용할 결과: {} 행 (PostProcess: {})",
                    finalResults.size(), hasPostProcessResults);

            // History 조회
            log.info("1단계: SemanticQuery 응답 히스토리 조회");
            List<Map<String, Object>> respondentHistory = promptBuilder.getRespondentHistory(workflowId);
            log.info("조회된 히스토리 개수: {}", respondentHistory != null ? respondentHistory.size() : 0);

            // QnA ID 생성
            log.info("2단계: QnA ID 생성");
            String qnaId = qnaService.createQnaId(state.getNodeId());
            log.info("생성된 QnA ID: {}", qnaId);

            // 프롬프트 생성
            log.info("3단계: SemanticQuery용 프롬프트 생성");
            PromptWithRetrieveTime promptWithRetrieveTime = promptBuilder.buildRespondentPromptWithFewShotsAndHistory(
                    userQuestion,
                    tablePipeForPrompt,
                    respondentHistory,
                    qnaId,
                    true,  // useSemanticQuery = true
                    state.getStartDate(),
                    state.getEndDate(),
                    workflowId
            );

            PromptTemplate promptTemplate = promptWithRetrieveTime.getPromptTemplate();
            String prompt = promptTemplate.build();
            log.info("생성된 프롬프트 길이: {} 문자", prompt.length());

            // QnA 질문 기록
            qnaService.updateQuestion(qnaId, prompt, "qwen_14b");

            // LLM 호출
            log.info("4단계: LLM 호출");
            long startTime = System.currentTimeMillis();
            String llmResponse = llmService.callSolver(prompt, qnaId);
            long endTime = System.currentTimeMillis();

            // LLM 프로파일링 기록
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordLlmCall(workflowId, elapsedTime, "semantic_respondent");
            log.info("LLM 응답 길이: {} 문자", llmResponse != null ? llmResponse.length() : 0);

            // QnA 답변 기록
            qnaService.recordAnswer(qnaId, llmResponse, promptWithRetrieveTime.getRetrieveTime());

            // fstring 응답 추출
            String fstringAnswer = LlmOutputHandler.extractFStringAnswer(llmResponse);
            if (fstringAnswer == null || fstringAnswer.trim().isEmpty()) {
                log.error("fstring 응답 생성에 실패했습니다.");
                state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("LLM_ERROR", "응답 생성에 실패했습니다."));
                return;
            }

            log.info("5단계: fstring 응답 처리");
            log.info("추출된 fstring 응답: {}", fstringAnswer);

            // 최종 답변 계산
            String finalAnswer = fstringRequest.computeFString(fstringAnswer, finalResults);

            // SemanticQuery의 모든 execution에 fstring과 finalAnswer 저장
            for (SemanticQueryWorkflowState.SemanticQueryExecution execution : executionMap.values()) {
                execution.setFString(fstringAnswer);
                execution.setFinalAnswer(finalAnswer);
            }

            // State에 최종 답변 저장
            state.setFinalAnswer(finalAnswer);

            log.info("=== SemanticQueryRespondentNode 실행 완료 ===");
            log.info("최종 응답 길이: {} 문자", finalAnswer != null ? finalAnswer.length() : 0);

            // WebSocket 메시지 전송
            Map<String, Object> data = new HashMap<>();
            data.put("total_entities", executionMap.size());
            data.put("result_rows", finalResults.size());
            data.put("has_post_process", hasPostProcessResults);
            data.put("entities_processed", executionMap.keySet());
            webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "semantic_respondent", data);

        } catch (Exception e) {
            log.error("SemanticQueryRespondentNode 실행 중 예외 발생", e);
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("SEMANTIC_RESPONDENT_ERROR", e.getMessage()));
        }
    }
}