package com.daquv.agent.workflow.semanticquery.node;

import com.daquv.agent.quvi.util.RequestProfiler;
import com.daquv.agent.workflow.WorkflowNode;
import com.daquv.agent.workflow.WorkflowState;
import com.daquv.agent.quvi.llmadmin.GenerationService;
import com.daquv.agent.quvi.util.ErrorHandler;
import com.daquv.agent.quvi.util.LlmOutputHandler;
import com.daquv.agent.workflow.prompt.PromptBuilder;
import com.daquv.agent.workflow.prompt.PromptBuilder.PromptWithRetrieveTime;
import com.daquv.agent.workflow.prompt.PromptTemplate;
import com.daquv.agent.quvi.requests.FstringRequest;
import com.daquv.agent.workflow.util.LLMRequest;
import com.daquv.agent.workflow.util.PipeTable;
import com.daquv.agent.quvi.util.WebSocketUtils;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class SemanticQueryRespondentNode implements WorkflowNode {

    @Autowired
    private LLMRequest llmService;

    @Autowired
    private PromptBuilder promptBuilder;

    @Autowired
    private GenerationService generationService;

    @Autowired
    private PipeTable pipeTable;

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
        return "semantic_query_respondent";
    }

    @Override
    public void execute(WorkflowState state) {
        String userQuestion = state.getUserQuestion();
        List<Map<String, Object>> queryResult = state.getQueryResult();
        String chainId = state.getWorkflowId();
        String startDate = state.getStartDate();
        String endDate = state.getEndDate();
        Boolean hasNext = state.getHasNext();
        Integer totalRows = state.getTotalRows();
        String selectedTable = state.getSelectedTable();

        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("SemanticQuery: 사용자 질문이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다."));
            return;
        }

        if (queryResult == null || queryResult.isEmpty()) {
            log.error("SemanticQuery: 쿼리 결과가 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("NO_DATA", "쿼리 결과가 없습니다."));
            return;
        }

        log.info("=== SemanticQuery RespondentNode 실행 시작 ===");
        log.info("SemanticQuery 사용자 질문: {}", userQuestion);
        log.info("SemanticQuery 쿼리 결과 행 수: {}", queryResult.size());
        log.info("SemanticQuery 체인 ID: {}", chainId);
        log.info("SemanticQuery hasNext 상태: {}", hasNext);
        log.info("SemanticQuery totalRows: {}", totalRows);
        log.info("SemanticQuery selectedTable: {}", selectedTable);

        // History 조회
        log.info("1단계: SemanticQuery 응답 히스토리 조회");
        List<Map<String, Object>> respondentHistory = promptBuilder.getRespondentHistory(chainId);
        log.info("SemanticQuery 조회된 히스토리 개수: {}", respondentHistory != null ? respondentHistory.size() : 0);

        // 쿼리 결과 정리 (파이썬의 delete_useless_col 역할)
        // 필요시 구현, 현재는 그대로 사용

        // 테이블 파이프 생성
        log.info("2단계: SemanticQuery 테이블 파이프 생성 시작");
        String tablePipe = pipeTable.pipeTable(queryResult);
        state.setTablePipe(tablePipe);
        log.info("SemanticQuery 테이블 파이프 생성 완료");

        // QnA ID 생성
        log.info("3단계: SemanticQuery QnA ID 생성");
        String qnaId = generationService.createQnaId(state.getNodeId());
        log.info("SemanticQuery 생성된 QnA ID: {}", qnaId);

        // hasNext에 따른 프롬프트 분기
        log.info("4단계: SemanticQuery hasNext 상태에 따른 프롬프트 분기");

        if (hasNext != null && hasNext) {
            // 페이지네이션 응답 생성
            log.info("✅ SemanticQuery 페이지네이션 응답 생성 시작");
            if (totalRows == null) totalRows = 0;

            log.info("SemanticQuery 페이지네이션용 프롬프트 생성 - 총 행 수: {}", totalRows);
            PromptTemplate promptTemplate = promptBuilder.buildPageRespondentPrompt(userQuestion, totalRows, respondentHistory, qnaId);

            log.info("5단계: SemanticQuery 프롬프트 생성 및 LLM 호출");
            String prompt = promptTemplate.build();
            log.info("SemanticQuery 생성된 프롬프트 길이: {} 문자", prompt.length());

            // QnA 질문 기록
            generationService.updateQuestion(qnaId, prompt, "qwen_14b");

            String finalAnswer = llmService.callQwenLlm(prompt, qnaId);
            log.info("SemanticQuery LLM 응답 길이: {} 문자", finalAnswer != null ? finalAnswer.length() : 0);

            // QnA 답변 기록
            generationService.recordAnswer(qnaId, finalAnswer, null);

            // 페이지네이션 응답 완료
            state.setFinalAnswer(finalAnswer);
            state.setQueryResult(queryResult);
            state.setTablePipe(tablePipe);

            log.info("SemanticQuery Final answer (paginated): {}", finalAnswer);

        } else {
            // 일반 응답 생성 (SemanticQuery는 비API이므로 날짜 정보 미사용)
            log.info("❌ SemanticQuery 일반 응답 생성 시작 (hasNext: false)");

            // SemanticQuery는 비API이므로 날짜 정보 미사용 (파이썬의 date_info = ())
            String dateStartForResponse = null;
            String dateEndForResponse = null;
            log.info("SemanticQuery 비API 모드: 날짜 정보 미사용");

            PromptWithRetrieveTime promptWithRetrieveTime = promptBuilder.buildRespondentPromptWithFewShotsAndHistory(
                    userQuestion, tablePipe, respondentHistory, qnaId, false, // isApi = false for SemanticQuery
                    dateStartForResponse, dateEndForResponse, chainId);

            PromptTemplate promptTemplate = promptWithRetrieveTime.getPromptTemplate();

            log.info("5단계: SemanticQuery 프롬프트 생성 및 LLM 호출");
            String prompt = promptTemplate.build();
            log.info("SemanticQuery 생성된 프롬프트 길이: {} 문자", prompt.length());

            // QnA 질문 기록
            generationService.updateQuestion(qnaId, prompt, "qwen_14b");

            long startTime = System.currentTimeMillis();
            String llmResponse = llmService.callSolver(prompt, qnaId);
            long endTime = System.currentTimeMillis();

            // LLM 프로파일링 기록
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordLlmCall(chainId, elapsedTime, "semantic_query_respondent");
            log.info("SemanticQuery LLM 응답 길이: {} 문자", llmResponse != null ? llmResponse.length() : 0);

            // QnA 답변 기록
            generationService.recordAnswer(qnaId, llmResponse, promptWithRetrieveTime.getRetrieveTime());

            // fstring 응답 추출 (파이썬의 handle_python_code_block)
            String fstringAnswer = LlmOutputHandler.extractFStringAnswer(llmResponse);
            if (fstringAnswer == null || fstringAnswer.trim().isEmpty()) {
                log.error("SemanticQuery fstring 응답 생성에 실패했습니다.");
                state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("LLM_ERROR", "fstring 응답 생성에 실패했습니다."));
                return;
            }

            log.info("6단계: SemanticQuery fstring 응답 처리");
            log.info("SemanticQuery 추출된 fstring 응답: {}", fstringAnswer);
            state.setFString(fstringAnswer);

            // 최종 답변 계산
            String finalAnswer = fstringRequest.computeFString(fstringAnswer, queryResult);

            // 미래 날짜 관련 처리 (SemanticQuery에서만 해당)
            if (state.getFutureDate() != null && state.getFutureDate()) {
                finalAnswer = "요청주신 시점은 제가 조회가 불가능한 시점이기에 오늘 날짜를 기준으로 조회했습니다. " + finalAnswer;
            }

            // 상태 업데이트
            state.setFinalAnswer(finalAnswer);
            state.setTablePipe(tablePipe);
            state.setQueryResult(queryResult);

            log.info("SemanticQuery Final answer: {}", finalAnswer);
        }

        log.info("=== SemanticQuery RespondentNode 실행 완료 ===");
        log.info("SemanticQuery 최종 응답 길이: {} 문자", state.getFinalAnswer() != null ? state.getFinalAnswer().length() : 0);
        log.info("SemanticQuery 최종 상태 - hasNext: {}, totalRows: {}, selectedTable: {}, finalAnswer: {}",
                hasNext, totalRows, selectedTable,
                state.getFinalAnswer() != null ? state.getFinalAnswer().substring(0, Math.min(100, state.getFinalAnswer().length())) + "..." : "null");

        // WebSocket 메시지 전송
        Map<String, Object> data = new HashMap<>();
        data.put("result_row", queryResult.size());
        data.put("result_column", queryResult.isEmpty() ? 0 : queryResult.get(0).size());
        data.put("selected_table", selectedTable);
        webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "semantic_query_respondent", data);
    }
}