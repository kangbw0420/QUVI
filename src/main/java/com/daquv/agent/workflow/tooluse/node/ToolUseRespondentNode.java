package com.daquv.agent.workflow.tooluse.node;

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
import com.daquv.agent.workflow.tooluse.ToolUseWorkflowNode;
import com.daquv.agent.workflow.tooluse.ToolUseWorkflowState;
import com.daquv.agent.workflow.util.LLMRequest;
import com.daquv.agent.workflow.util.PipeTableUtils;
import com.daquv.agent.quvi.util.WebSocketUtils;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class ToolUseRespondentNode implements ToolUseWorkflowNode {

    @Autowired
    private LLMRequest llmService;

    @Autowired
    private PromptBuilder promptBuilder;

    @Autowired
    private GenerationService generationService;

    @Autowired
    private PipeTableUtils pipeTableUtils;

    private final FstringRequest fstringRequest;

    @Autowired
    private WebSocketUtils webSocketUtils;

    @Autowired
    private RequestProfiler requestProfiler;

    public ToolUseRespondentNode(FstringRequest fstringRequest) {
        this.fstringRequest = fstringRequest;
    }

    @Override
    public String getId() {
        return "tooluse_respondent";
    }

    @Override
    public void execute(ToolUseWorkflowState state) {
        String userQuestion = state.getUserQuestion();
        List<Map<String, Object>> queryResult = state.getQueryResult();
        String chainId = state.getWorkflowId();
        String startDate = state.getStartDate();
        String endDate = state.getEndDate();
        Boolean hasNext = state.getHasNext();
        Integer totalRows = state.getTotalRows();
        String selectedApi = state.getSelectedApi();

        if (userQuestion == null || userQuestion.trim().isEmpty()) {
            log.error("ToolUse: 사용자 질문이 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("INVALID_INPUT", "사용자 질문이 없습니다."));
            return;
        }

        if (queryResult == null || queryResult.isEmpty()) {
            log.error("ToolUse: 쿼리 결과가 없습니다.");
            state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("NO_DATA", "쿼리 결과가 없습니다."));
            return;
        }

        log.info("=== ToolUse RespondentNode 실행 시작 ===");
        log.info("ToolUse 사용자 질문: {}", userQuestion);
        log.info("ToolUse 쿼리 결과 행 수: {}", queryResult.size());
        log.info("ToolUse 체인 ID: {}", chainId);
        log.info("ToolUse hasNext 상태: {}", hasNext);
        log.info("ToolUse totalRows: {}", totalRows);
        log.info("ToolUse selectedApi: {}", selectedApi);

        // History 조회 (ToolUse용)
        log.info("1단계: ToolUse 응답 히스토리 조회");
        List<Map<String, Object>> respondentHistory = promptBuilder.getRespondentHistory(chainId);
        log.info("ToolUse 조회된 히스토리 개수: {}", respondentHistory != null ? respondentHistory.size() : 0);

        // 테이블 파이프 생성
        log.info("2단계: ToolUse 테이블 파이프 생성 시작");
        String tablePipe = pipeTableUtils.pipeTable(queryResult);
        state.setTablePipe(tablePipe);
        log.info("ToolUse 테이블 파이프 생성 완료");

        // QnA ID 생성
        log.info("3단계: ToolUse QnA ID 생성");
        String qnaId = generationService.createQnaId(state.getNodeId());
        log.info("ToolUse 생성된 QnA ID: {}", qnaId);

        // hasNext에 따른 프롬프트 분기
        log.info("4단계: ToolUse hasNext 상태에 따른 프롬프트 분기");

        if (hasNext != null && hasNext) {
            // 페이지네이션 응답 생성 (ToolUse용)
            log.info("✅ ToolUse 페이지네이션 응답 생성 시작");
            if (totalRows == null) totalRows = 0;

            log.info("ToolUse 페이지네이션용 프롬프트 생성 - 총 행 수: {}", totalRows);
            PromptTemplate promptTemplate = promptBuilder.buildPageRespondentPrompt(userQuestion, totalRows, respondentHistory, qnaId);

            log.info("5단계: ToolUse 프롬프트 생성 및 LLM 호출");
            String prompt = promptTemplate.build();
            log.info("ToolUse 생성된 프롬프트 길이: {} 문자", prompt.length());

            // QnA 질문 기록
            generationService.updateQuestion(qnaId, prompt, "qwen_14b");

            String finalAnswer = llmService.callQwenLlm(prompt, qnaId);
            log.info("ToolUse LLM 응답 길이: {} 문자", finalAnswer != null ? finalAnswer.length() : 0);

            // QnA 답변 기록
            generationService.recordAnswer(qnaId, finalAnswer, null);

            // 페이지네이션 응답 완료
            state.setFinalAnswer(finalAnswer);
            state.setQueryResult(queryResult);
            state.setTablePipe(tablePipe);

            log.info("ToolUse Final answer (paginated): {}", finalAnswer);

        } else {
            // 일반 응답 생성 (ToolUse는 항상 API이므로 날짜 정보 사용)
            log.info("❌ ToolUse 일반 응답 생성 시작 (hasNext: false)");

            // ToolUse는 항상 API이므로 날짜 정보 사용
            String dateStartForResponse = startDate;
            String dateEndForResponse = endDate;
            log.info("ToolUse API 모드: 날짜 정보 사용 - startDate: {}, endDate: {}", startDate, endDate);

            PromptWithRetrieveTime promptWithRetrieveTime = promptBuilder.buildRespondentPromptWithFewShotsAndHistory(
                    userQuestion, tablePipe, respondentHistory, qnaId, true, // isApi = true for ToolUse
                    dateStartForResponse, dateEndForResponse, chainId);

            PromptTemplate promptTemplate = promptWithRetrieveTime.getPromptTemplate();

            log.info("5단계: ToolUse 프롬프트 생성 및 LLM 호출");
            String prompt = promptTemplate.build();
            log.info("ToolUse 생성된 프롬프트 길이: {} 문자", prompt.length());

            // QnA 질문 기록
            generationService.updateQuestion(qnaId, prompt, "qwen_14b");

            long startTime = System.currentTimeMillis();
            String llmResponse = llmService.callSolver(prompt, qnaId);
            long endTime = System.currentTimeMillis();

            // LLM 프로파일링 기록
            double elapsedTime = (endTime - startTime) / 1000.0;
            requestProfiler.recordLlmCall(chainId, elapsedTime, "tooluse_respondent");
            log.info("ToolUse LLM 응답 길이: {} 문자", llmResponse != null ? llmResponse.length() : 0);

            // QnA 답변 기록
            generationService.recordAnswer(qnaId, llmResponse, promptWithRetrieveTime.getRetrieveTime());

            // fstring 응답 추출
            String fstringAnswer = LlmOutputHandler.extractFStringAnswer(llmResponse);
            if (fstringAnswer == null || fstringAnswer.trim().isEmpty()) {
                log.error("ToolUse fstring 응답 생성에 실패했습니다.");
                state.setFinalAnswer(ErrorHandler.getWorkflowErrorMessage("LLM_ERROR", "fstring 응답 생성에 실패했습니다."));
                return;
            }

            log.info("6단계: ToolUse fstring 응답 처리");
            log.info("ToolUse 추출된 fstring 응답: {}", fstringAnswer);
            state.setFString(fstringAnswer);

            // 최종 답변 계산
            String finalAnswer = fstringRequest.computeFString(fstringAnswer, queryResult);

            // 상태 업데이트
            state.setFinalAnswer(finalAnswer);
            state.setTablePipe(tablePipe);
            state.setQueryResult(queryResult);

            log.info("ToolUse Final answer: {}", finalAnswer);
        }

        log.info("=== ToolUse RespondentNode 실행 완료 ===");
        log.info("ToolUse 최종 응답 길이: {} 문자", state.getFinalAnswer() != null ? state.getFinalAnswer().length() : 0);
        log.info("ToolUse 최종 상태 - hasNext: {}, totalRows: {}, selectedApi: {}, finalAnswer: {}",
                hasNext, totalRows, selectedApi,
                state.getFinalAnswer() != null ? state.getFinalAnswer().substring(0, Math.min(100, state.getFinalAnswer().length())) + "..." : "null");

        // WebSocket 메시지 전송
        Map<String, Object> data = new HashMap<>();
        data.put("result_row", queryResult.size());
        data.put("result_column", queryResult.isEmpty() ? 0 : queryResult.get(0).size());
        data.put("selected_api", selectedApi);
        webSocketUtils.sendNodeEnd(state.getWebSocketSession(), "tooluse_respondent", data);
    }
}