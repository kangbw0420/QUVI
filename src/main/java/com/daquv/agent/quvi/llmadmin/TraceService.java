package com.daquv.agent.quvi.llmadmin;

import com.daquv.agent.quvi.entity.Chain;
import com.daquv.agent.quvi.entity.Trace;
import com.daquv.agent.quvi.repository.ChainRepository;
import com.daquv.agent.quvi.repository.TraceRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class TraceService {

    private static final Logger log = LoggerFactory.getLogger(TraceService.class);
    private final TraceRepository traceRepository;
    private final ChainRepository chainRepository;

    public TraceService(TraceRepository traceRepository, ChainRepository chainRepository) {
        this.traceRepository = traceRepository;
        this.chainRepository = chainRepository;
    }

    /**
     * 노드 실행 시작 시 trace 기록 생성
     * 
     * @param chainId 체인 ID
     * @param nodeType 노드 타입
     * @return 생성된 trace ID
     */
    @Transactional
    public String createTrace(String chainId, String nodeType) {
        log.info("createTrace start - chainId: {}, nodeType: {}", chainId, nodeType);
        
        try {
            String traceId = UUID.randomUUID().toString();
            
            // Chain 조회
            Chain chain = chainRepository.findById(chainId)
                    .orElseThrow(() -> new IllegalArgumentException("Chain not found: " + chainId));
            
            // Trace 생성
            Trace trace = new Trace();
            trace.setId(traceId);
            trace.setChain(chain);
            trace.setNodeType(nodeType);
            trace.setTraceStatus(Trace.TraceStatus.active);
            
            traceRepository.save(trace);
            
            log.info("createTrace end - traceId: {}", traceId);
            return traceId;
            
        } catch (Exception e) {
            log.error("Error in createTrace - chainId: {}, nodeType: {}", chainId, nodeType, e);
            throw new RuntimeException("Failed to create trace", e);
        }
    }

    /**
     * 노드 실행 완료 시 trace 상태 업데이트
     * 
     * @param traceId 트레이스 ID
     * @return 성공 여부
     */
    @Transactional
    public boolean completeTrace(String traceId) {
        log.info("completeTrace start - traceId: {}", traceId);
        
        try {
            Trace trace = traceRepository.findById(traceId)
                    .orElseThrow(() -> new IllegalArgumentException("Trace not found: " + traceId));
            
            trace.completeTrace();
            traceRepository.save(trace);
            
            log.info("completeTrace end - traceId: {}", traceId);
            return true;
            
        } catch (Exception e) {
            log.error("Error in completeTrace - traceId: {}", traceId, e);
            throw new RuntimeException("Failed to complete trace", e);
        }
    }

    /**
     * trace 상태를 error로 변경하고 종료 시간 기록
     * 
     * @param traceId 트레이스 ID
     * @return 성공 여부
     */
    @Transactional
    public boolean markTraceError(String traceId) {
        log.info("markTraceError start - traceId: {}", traceId);
        
        try {
            Trace trace = traceRepository.findById(traceId)
                    .orElseThrow(() -> new IllegalArgumentException("Trace not found: " + traceId));
            
            trace.completeTrace(); // 종료 시간 기록
            trace.updateStatus(Trace.TraceStatus.error); // 상태를 error로 변경
            traceRepository.save(trace);
            
            log.info("markTraceError end - traceId: {}", traceId);
            return true;
            
        } catch (Exception e) {
            log.error("Error in markTraceError - traceId: {}", traceId, e);
            throw new RuntimeException("Failed to mark trace error", e);
        }
    }

    /**
     * 트레이스 조회
     * 
     * @param traceId 트레이스 ID
     * @return 트레이스 정보 (Optional)
     */
    public Optional<Trace> getTrace(String traceId) {
        log.info("getTrace - traceId: {}", traceId);
        return traceRepository.findById(traceId);
    }

    /**
     * 체인 ID로 트레이스 목록 조회
     * 
     * @param chainId 체인 ID
     * @return 트레이스 목록
     */
    public List<Trace> getTracesByChainId(String chainId) {
        log.info("getTracesByChainId - chainId: {}", chainId);
        return traceRepository.findByChainIdOrderByTraceStartAsc(chainId);
    }

    /**
     * 트레이스 상태로 트레이스 목록 조회
     * 
     * @param status 트레이스 상태
     * @return 트레이스 목록
     */
    public List<Trace> getTracesByStatus(Trace.TraceStatus status) {
        log.info("getTracesByStatus - status: {}", status);
        return traceRepository.findByTraceStatus(status);
    }

    /**
     * 노드 타입으로 트레이스 목록 조회
     * 
     * @param nodeType 노드 타입
     * @return 트레이스 목록
     */
    public List<Trace> getTracesByNodeType(String nodeType) {
        log.info("getTracesByNodeType - nodeType: {}", nodeType);
        return traceRepository.findByNodeType(nodeType);
    }
}
