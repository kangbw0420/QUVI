package com.daquv.agent.quvi.llmadmin;

import com.daquv.agent.quvi.entity.Node;
import com.daquv.agent.quvi.entity.Workflow;
import com.daquv.agent.quvi.repository.WorkflowRepository;
import com.daquv.agent.quvi.repository.NodeRepository;
import com.daquv.agent.quvi.util.DatabaseProfilerAspect;
import com.daquv.agent.quvi.util.RequestProfiler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class NodeService {

    private static final Logger log = LoggerFactory.getLogger(NodeService.class);
    private final NodeRepository nodeRepository;
    private final WorkflowRepository workflowRepository;

    @Autowired
    private RequestProfiler requestProfiler;


    public NodeService(NodeRepository nodeRepository, WorkflowRepository workflowRepository) {
        this.nodeRepository = nodeRepository;
        this.workflowRepository = workflowRepository;
    }

    /**
     * 노드 실행 시작 시 trace 기록 생성
     *
     * @param workflowId 체인 ID
     * @param nodeName 노드 타입
     * @return 생성된 trace ID
     */
    @Transactional
    public String createNode(String workflowId, String nodeName) {
        log.info("createNode start - workflowId: {}, nodeType: {}", workflowId, nodeName);

        DatabaseProfilerAspect.setWorkflowId(workflowId);
        log.debug("TraceService에서 workflowId 설정: {}", workflowId);

        try {
            String traceId = UUID.randomUUID().toString();

            // Chain 조회
            Workflow workflow = workflowRepository.findById(workflowId)
                    .orElseThrow(() -> new IllegalArgumentException("Node not found: " + workflowId));

            // Trace 생성
            Node node = new Node();
            node.setNodeId(traceId);
            node.setWorkflow(workflow);
            node.setNodeName(nodeName);
            node.setNodeStatus(Node.NodeStatus.active);

            nodeRepository.save(node);

            log.info("createNode end - nodeId: {}", traceId);
            return traceId;

        } catch (Exception e) {
            log.error("Error in createNode - workflowId: {}, nodeName: {}", workflowId, nodeName, e);
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
    public boolean completeNode(String traceId) {
        log.info("completeNode start - traceId: {}", traceId);

        try {
            Node node = nodeRepository.findById(traceId)
                    .orElseThrow(() -> new IllegalArgumentException("Node not found: " + traceId));

            node.completeTrace();
            nodeRepository.save(node);

            log.info("completeNode end - traceId: {}", traceId);
            return true;

        } catch (Exception e) {
            log.error("Error in completeNode - traceId: {}", traceId, e);
            throw new RuntimeException("Failed to complete node", e);
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
            Node node = nodeRepository.findById(traceId)
                    .orElseThrow(() -> new IllegalArgumentException("Trace not found: " + traceId));

            node.completeTrace(); // 종료 시간 기록
            node.updateStatus(Node.NodeStatus.error); // 상태를 error로 변경
            nodeRepository.save(node);

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
    public Optional<Node> getTrace(String traceId) {
        log.info("getTrace - traceId: {}", traceId);

        String chainId = null;
        long startTime = System.currentTimeMillis();

            Optional<Node> traceOpt = nodeRepository.findById(traceId);

            // chainId 추출 (trace가 존재할 때만)
            if (traceOpt.isPresent()) {
                chainId = traceOpt.get().getWorkflow().getWorkflowId();
            }

            return traceOpt;

    }

    /**
     * 체인 ID로 트레이스 목록 조회
     *
     * @param chainId 체인 ID
     * @return 트레이스 목록
     */
    public List<Node> getTracesByChainId(String chainId) {
        log.info("getTracesByChainId - chainId: {}", chainId);

        long startTime = System.currentTimeMillis();

            return nodeRepository.findByWorkflowIdOrderByNodeStartAsc(chainId);

    }

    /**
     * 트레이스 상태로 트레이스 목록 조회
     *
     * @param status 트레이스 상태
     * @return 트레이스 목록
     */
    public List<Node> getTracesByStatus(Node.NodeStatus status) {
        log.info("getTracesByStatus - status: {}", status);

            return nodeRepository.findByNodeStatus(status);
    }

    /**
     * 노드 타입으로 트레이스 목록 조회
     *
     * @param nodeType 노드 타입
     * @return 트레이스 목록
     */
    public List<Node> getTracesByNodeType(String nodeType) {
        log.info("getTracesByNodeType - nodeType: {}", nodeType);

        // 이 메서드는 특정 chainId와 연관되지 않으므로 null로 처리

            return nodeRepository.findByNodeName(nodeType);

    }

    /**
     * 노드 상태를 JSON으로 업데이트
     *
     * @param nodeId 노드 ID
     * @param stateJson 상태 JSON 문자열
     * @return 성공 여부
     */
    @Transactional
    public boolean updateNodeStateJson(String nodeId, String stateJson) {
        log.info("updateNodeStateJson start - nodeId: {}", nodeId);

        try {
            Node node = nodeRepository.findById(nodeId)
                    .orElseThrow(() -> new IllegalArgumentException("Node not found: " + nodeId));

            node.setNodeStateAsJson(stateJson);
            nodeRepository.save(node);

            log.info("updateNodeStateJson end - nodeId: {}", nodeId);
            return true;

        } catch (Exception e) {
            log.error("Error in updateNodeStateJson - nodeId: {}", nodeId, e);
            throw new RuntimeException("Failed to update node state JSON", e);
        }
    }
}
