package com.daquv.agent.quvi.llmadmin;

import com.daquv.agent.quvi.entity.Node;
import com.daquv.agent.quvi.entity.Generation;
//import com.daquv.agent.quvi.entity.Fewshot;
import com.daquv.agent.quvi.repository.QnaRepository;
import com.daquv.agent.quvi.repository.TraceRepository;
//import com.daquv.agent.quvi.repository.FewshotRepository;
import com.daquv.agent.quvi.util.DatabaseProfilerAspect;
import com.daquv.agent.quvi.util.RequestProfiler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import javax.servlet.http.HttpServletRequest;
import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class QnaService {

    private static final Logger log = LoggerFactory.getLogger(QnaService.class);
    private final QnaRepository qnaRepository;
    private final TraceRepository traceRepository;
//    private final FewshotRepository fewshotRepository;

    @Autowired
    private RequestProfiler requestProfiler;

    public QnaService(QnaRepository qnaRepository, TraceRepository traceRepository
                    ) {
        this.qnaRepository = qnaRepository;
        this.traceRepository = traceRepository;
    }

    /**
     * 메시지 문자열 포맷팅 (연속된 개행문자를 하나로 통일하고 앞뒤 공백 제거)
     */
    public String formatMessageStr(String msgStr) {
        return msgStr.replace("\\n", "\n").trim();
    }

    /**
     * QnA ID를 생성하고 기본 레코드를 생성합니다.
     */
    @Transactional
    public String createQnaId(String traceId) {
        log.info("createQnaId start - traceId: {}", traceId);

        String chainId = getCurrentChainId();
        if (chainId != null) {
            DatabaseProfilerAspect.setChainId(chainId);
            log.debug("QnaService에서 chainId 설정: {}", chainId);
        }

        long startTime = System.currentTimeMillis();
        try {
            String qnaId = UUID.randomUUID().toString();

            // Trace 조회
            Node node = traceRepository.findById(traceId)
                    .orElseThrow(() -> new IllegalArgumentException("Trace not found: " + traceId));

            // Qna 생성
            Generation generation = new Generation();
            generation.setId(qnaId);
            generation.setNode(node);
            generation.setQuestionTimestamp(java.time.LocalDateTime.now());

            qnaRepository.save(generation);

            log.info("createQnaId end - qnaId: {}", qnaId);
            return qnaId;

        } catch (Exception e) {
            log.error("Error in createQnaId - traceId: {}", traceId, e);
            throw new RuntimeException("Failed to create QnA ID", e);
        }
    }

    /**
     * 단일 Few-shot 예제를 저장합니다.
     */
    @Transactional
    public boolean recordFewshot(String qnaId, String retrieved, String human, String ai, int order) {
        log.info("recordFewshot start - qnaId: {}, retrieved: {}, human: {}, ai: {}, order: {}",
                qnaId, retrieved, human, ai, order);

        String chainId = getCurrentChainId();
        if (chainId != null) {
            DatabaseProfilerAspect.setChainId(chainId);
            log.debug("QnaService.recordFewshot에서 chainId 설정: {}", chainId);
        }

        long startTime = System.currentTimeMillis();
        try {
            // Qna(Generation) 존재 여부 확인
            Generation generation = qnaRepository.findById(qnaId)
                    .orElseThrow(() -> new IllegalArgumentException("QnA not found: " + qnaId));

            log.debug("Generation found: {}", generation.getId());

            String fewshotId = UUID.randomUUID().toString();

//            // Fewshot 생성
//            Fewshot fewshot = Fewshot.builder()
//                    .id(fewshotId)
//                    .generation(generation)
//                    .fewshotRetrieved(retrieved)
//                    .fewshotHuman(human)
//                    .fewshotAi(ai)
//                    .orderSeq(order)
//                    .build();
//
//            fewshotRepository.save(fewshot);

            log.info("recordFewshot end - fewshotId: {}", fewshotId);
            return true;

        } catch (Exception e) {
            log.error("Error in recordFewshot - qnaId: {}, retrieved: {}, human: {}, ai: {}, order: {}",
                    qnaId, retrieved, human, ai, order, e);
            throw new RuntimeException("Failed to record fewshot", e);
        }
    }

    /**
     * QnA 레코드에 질문과 모델 정보를 업데이트합니다.
     *
     * @param qnaId QnA ID
     * @param question 질문 (ChatPromptTemplate 또는 String)
     * @param model 모델명
     * @return 성공 여부
     */
    @Transactional
    public boolean updateQuestion(String qnaId, Object question, String model) {
        log.info("updateQuestion start - qnaId: {}, question: {}, model: {}", qnaId, question, model);

        String chainId = getCurrentChainId();
        long startTime = System.currentTimeMillis();

        try {
            // ChatPromptTemplate인 경우 문자열로 변환
            String questionStr;
            if (question != null) {
                questionStr = formatMessageStr(question.toString());
            } else {
                questionStr = null;
            }

            Generation generation = qnaRepository.findById(qnaId)
                    .orElseThrow(() -> new IllegalArgumentException("QnA not found: " + qnaId));

            generation.setPrompt(questionStr);
            generation.setModel(model);

            qnaRepository.save(generation);

            log.info("updateQuestion end - qnaId: {}", qnaId);
            return true;

        } catch (Exception e) {
            log.error("Error in updateQuestion - qnaId: {}, question: {}, model: {}", qnaId, question, model, e);
            throw new RuntimeException("Failed to update question", e);
        }
    }

    /**
     * LLM 응답을 받은 시점에 답변 기록
     *
     * @param qnaId QnA ID
     * @param answer 답변
     * @param retrieveTime 검색 시간 (초)
     * @return 성공 여부
     */
    @Transactional
    public boolean recordAnswer(String qnaId, String answer, BigDecimal retrieveTime) {
        log.info("recordAnswer start - qnaId: {}, answer: {}, retrieveTime: {}", qnaId, answer, retrieveTime);

        String chainId = getCurrentChainId();
        long startTime = System.currentTimeMillis();

        try {
            Generation generation = qnaRepository.findById(qnaId)
                    .orElseThrow(() -> new IllegalArgumentException("QnA not found: " + qnaId));

            generation.setAnswer(answer);
//            generation.setRetrieveTime(retrieveTime);

            qnaRepository.save(generation);

            log.info("recordAnswer end - qnaId: {}", qnaId);
            return true;

        } catch (Exception e) {
            log.error("Error in recordAnswer - qnaId: {}, answer: {}, retrieveTime: {}",
                    qnaId, answer, retrieveTime, e);
            throw new RuntimeException("Failed to record answer", e);
        }
    }

    /**
     * QnA 조회
     *
     * @param qnaId QnA ID
     * @return QnA 정보 (Optional)
     */
    public Optional<Generation> getQna(String qnaId) {
        log.info("getQna - qnaId: {}", qnaId);
        return qnaRepository.findById(qnaId);
    }

    /**
     * 트레이스 ID로 QnA 목록 조회
     *
     * @param traceId 트레이스 ID
     * @return QnA 목록
     */
    public List<Generation> getQnasByTraceId(String traceId) {
        log.info("getQnasByTraceId - traceId: {}", traceId);
        return qnaRepository.findByTraceIdOrderByQuestionTimestampAsc(traceId);
    }

    /**
     * 모델로 QnA 목록 조회
     *
     * @param model 모델명
     * @return QnA 목록
     */
    public List<Generation> getQnasByModel(String model) {
        log.info("getQnasByModel - model: {}", model);
        return qnaRepository.findByModel(model);
    }

    /**
     * 답변이 있는 QnA 목록 조회
     *
     * @return 답변이 있는 QnA 목록
     */
    public List<Generation> getQnasWithAnswer() {
        log.info("getQnasWithAnswer");
        return qnaRepository.findByAnswerIsNotNull();
    }
//
//    /**
//     * QnA ID로 Fewshot 목록 조회
//     *
//     * @param qnaId QnA ID
//     * @return Fewshot 목록
//     */
//    public List<Fewshot> getFewshotsByQnaId(String qnaId) {
//        log.info("getFewshotsByQnaId - qnaId: {}", qnaId);
//        return fewshotRepository.findByQnaIdOrderByOrderSeqAsc(qnaId);
//    }

    /**
     * 모델별 QnA 수 조회
     *
     * @param model 모델명
     * @return QnA 수
     */
    public long countByModel(String model) {
        log.info("countByModel - model: {}", model);
        return qnaRepository.countByModel(model);
    }

    /**
     * 답변이 있는 QnA 수 조회
     *
     * @return 답변이 있는 QnA 수
     */
    public long countWithAnswer() {
        log.info("countWithAnswer");
        return qnaRepository.countByAnswerIsNotNull();
    }

//    /**
//     * 평균 검색 시간 조회
//     *
//     * @return 평균 검색 시간
//     */
//    public BigDecimal getAverageRetrieveTime() {
//        log.info("getAverageRetrieveTime");
//        return qnaRepository.getAverageRetrieveTime();
//    }

    private String getCurrentChainId() {
        try {
            RequestAttributes requestAttributes = RequestContextHolder.getRequestAttributes();
            if (requestAttributes instanceof ServletRequestAttributes) {
                HttpServletRequest request = ((ServletRequestAttributes) requestAttributes).getRequest();

                Object chainIdAttr = request.getAttribute("chainId");
                if (chainIdAttr != null) {
                    return chainIdAttr.toString();
                }

                Object xChainIdAttr = request.getAttribute("X-Chain-Id");
                if (xChainIdAttr != null) {
                    return xChainIdAttr.toString();
                }
            }
        } catch (Exception e) {
            log.debug("getCurrentChainId 실패: {}", e.getMessage());
        }
        return null;
    }
}