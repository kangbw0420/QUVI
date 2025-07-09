package com.daquv.agent.quvi.llmadmin;

import com.daquv.agent.quvi.entity.Qna;
import com.daquv.agent.quvi.entity.Trace;
import com.daquv.agent.quvi.entity.Fewshot;
import com.daquv.agent.quvi.repository.QnaRepository;
import com.daquv.agent.quvi.repository.TraceRepository;
import com.daquv.agent.quvi.repository.FewshotRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

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
    private final FewshotRepository fewshotRepository;

    public QnaService(QnaRepository qnaRepository, TraceRepository traceRepository, 
                     FewshotRepository fewshotRepository) {
        this.qnaRepository = qnaRepository;
        this.traceRepository = traceRepository;
        this.fewshotRepository = fewshotRepository;
    }

    /**
     * 메시지 문자열 포맷팅 (연속된 개행문자를 하나로 통일하고 앞뒤 공백 제거)
     * 
     * @param msgStr 메시지 문자열
     * @return 포맷팅된 문자열
     */
    public String formatMessageStr(String msgStr) {
        return msgStr.replace("\\n", "\n").trim();
    }

    /**
     * QnA ID를 생성하고 기본 레코드를 생성합니다.
     * 
     * @param traceId 추적 ID
     * @return 생성된 qna ID
     */
    @Transactional
    public String createQnaId(String traceId) {
        log.info("createQnaId start - traceId: {}", traceId);
        
        try {
            String qnaId = UUID.randomUUID().toString();
            
            // Trace 조회
            Trace trace = traceRepository.findById(traceId)
                    .orElseThrow(() -> new IllegalArgumentException("Trace not found: " + traceId));
            
            // Qna 생성
            Qna qna = new Qna();
            qna.setId(qnaId);
            qna.setTrace(trace);
            qna.setQuestionTimestamp(java.time.LocalDateTime.now());
            
            qnaRepository.save(qna);
            
            log.info("createQnaId end - qnaId: {}", qnaId);
            return qnaId;
            
        } catch (Exception e) {
            log.error("Error in createQnaId - traceId: {}", traceId, e);
            throw new RuntimeException("Failed to create QnA ID", e);
        }
    }

    /**
     * 단일 Few-shot 예제를 저장합니다.
     * 
     * @param qnaId QnA ID
     * @param retrieved 벡터 스토어에서 검색된 원본 질문
     * @param human 실제 사용된 human prompt
     * @param ai AI 응답
     * @param order 순서
     * @return 성공 여부
     */
    @Transactional
    public boolean recordFewshot(String qnaId, String retrieved, String human, String ai, int order) {
        log.info("recordFewshot start - qnaId: {}, retrieved: {}, human: {}, ai: {}, order: {}", 
                qnaId, retrieved, human, ai, order);
        
        try {
            String fewshotId = UUID.randomUUID().toString();
            
            // Qna 조회
            Qna qna = qnaRepository.findById(qnaId)
                    .orElseThrow(() -> new IllegalArgumentException("QnA not found: " + qnaId));
            
            // Fewshot 생성
            Fewshot fewshot = new Fewshot();
            fewshot.setId(fewshotId);
            fewshot.setQna(qna);
            fewshot.setFewshotRetrieved(retrieved);
            fewshot.setFewshotHuman(human);
            fewshot.setFewshotAi(ai);
            fewshot.setOrderSeq(order);
            
            fewshotRepository.save(fewshot);
            
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
        
        try {
            // ChatPromptTemplate인 경우 문자열로 변환
            String questionStr;
            if (question != null) {
                questionStr = formatMessageStr(question.toString());
            } else {
                questionStr = null;
            }
            
            Qna qna = qnaRepository.findById(qnaId)
                    .orElseThrow(() -> new IllegalArgumentException("QnA not found: " + qnaId));
            
            qna.setQuestion(questionStr);
            qna.setModel(model);
            
            qnaRepository.save(qna);
            
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
        
        try {
            Qna qna = qnaRepository.findById(qnaId)
                    .orElseThrow(() -> new IllegalArgumentException("QnA not found: " + qnaId));
            
            qna.setAnswer(answer);
            qna.setRetrieveTime(retrieveTime);
            
            qnaRepository.save(qna);
            
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
    public Optional<Qna> getQna(String qnaId) {
        log.info("getQna - qnaId: {}", qnaId);
        return qnaRepository.findById(qnaId);
    }

    /**
     * 트레이스 ID로 QnA 목록 조회
     * 
     * @param traceId 트레이스 ID
     * @return QnA 목록
     */
    public List<Qna> getQnasByTraceId(String traceId) {
        log.info("getQnasByTraceId - traceId: {}", traceId);
        return qnaRepository.findByTraceIdOrderByQuestionTimestampAsc(traceId);
    }

    /**
     * 모델로 QnA 목록 조회
     * 
     * @param model 모델명
     * @return QnA 목록
     */
    public List<Qna> getQnasByModel(String model) {
        log.info("getQnasByModel - model: {}", model);
        return qnaRepository.findByModel(model);
    }

    /**
     * 답변이 있는 QnA 목록 조회
     * 
     * @return 답변이 있는 QnA 목록
     */
    public List<Qna> getQnasWithAnswer() {
        log.info("getQnasWithAnswer");
        return qnaRepository.findByAnswerIsNotNull();
    }

    /**
     * QnA ID로 Fewshot 목록 조회
     * 
     * @param qnaId QnA ID
     * @return Fewshot 목록
     */
    public List<Fewshot> getFewshotsByQnaId(String qnaId) {
        log.info("getFewshotsByQnaId - qnaId: {}", qnaId);
        return fewshotRepository.findByQnaIdOrderByOrderSeqAsc(qnaId);
    }

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

    /**
     * 평균 검색 시간 조회
     * 
     * @return 평균 검색 시간
     */
    public BigDecimal getAverageRetrieveTime() {
        log.info("getAverageRetrieveTime");
        return qnaRepository.getAverageRetrieveTime();
    }
}
