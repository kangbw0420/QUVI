package com.daquv.agent.integration;

import com.daquv.agent.integration.ifagent.IfExecutor;
import com.daquv.agent.integration.ifagent.IfQueryUtils;
import com.daquv.agent.quvi.requests.QueryRequest;
import com.daquv.agent.quvi.requests.ColumnRequest;
import com.daquv.agent.workflow.supervisor.SupervisorWorkflowState;
import com.daquv.agent.workflow.util.ArrowData;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.arrow.memory.RootAllocator;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static com.daquv.agent.integration.ifagent.IfExecutor.FETCH_ALL;

@Slf4j
@Component
@RequiredArgsConstructor
public class BranchRunSql {

    // private static final int PAGE_SIZE = 100;

    private final QueryRequest queryRequest;
    private final IfQueryUtils ifQueryUtils;
    private final IfExecutor ifExecutor;
    private final ColumnRequest columnRequest;
    private final QueryRequest queryRequest1;
    private final NameMappingService nameMappingService;

    @Value("${view-table.dialect}")
    private String DIALECT;


    /**
     * SQL을 실행하고 결과를 execution에 채워 넣는다.
     */
    public void executeSql(String sqlQuery,
                                           SupervisorWorkflowState supervisorState,
                                           SupervisorWorkflowState.WorkflowExecution execution) {
        try {
            String companyId = supervisorState.getUserInfo().getCompanyId();

            log.info("=== RunSql 실행 시작 ===");
            log.info("원본 SQL 쿼리: {}", sqlQuery);

            // 1. 권한 있는 회사/계좌 검사 추가
           String queryWithComCondition = ifQueryUtils.addComCondition(sqlQuery, companyId);
           log.info("회사 조건 추가 후: {}", queryWithComCondition);

            Map<String, String> stockMappings = nameMappingService.getStockMappings();
            Map<String, String> bankMappings = nameMappingService.getBankMappings();

            // 2. 주식종목/은행명 매핑 변환
            String queryWithStock = columnRequest.transformStockNames(queryWithComCondition, stockMappings);
            String queryWithBank = columnRequest.transformBankNames(queryWithStock, bankMappings);
            log.info("주식종목/은행명 매핑 후: {}", queryWithBank);

            // String columnName = selectedTable.equals("trsc") ? "trsc_dt" : "reg_dt";
            // String conditionType = selectedTable.equals("trsc") ? "between" : "equals";
            // List<String> transformValues = new ArrayList<>();
            // if (selectedTable.equals("trsc")) {
            //     transformValues.add(execution.getExecutionStartDate());
            //     transformValues.add(execution.getExecutionEndDate());
            // } else {
            //     transformValues.add(execution.getExecutionEndDate());
            // }

            // 3. 날짜 조건 추가
            // String queryRightDate = columnRequest.whereClause(queryWithBank, columnName, conditionType, transformValues, true);

            // 3. ORDER BY 추가
            String queryWithOrderBy = queryRequest1.addOrderBy(queryWithBank);
            log.info("ORDER BY 추가 후: {}", queryWithOrderBy);

            // 4. View Table 적용을 위한 파라미터 준비
            List<String> listOfUserInfo = supervisorState.getUserInfo().toArray();
            List<String> parameters = new ArrayList<>(listOfUserInfo);

            parameters.add(execution.getExecutionStartDate());
            parameters.add(execution.getExecutionEndDate());

            // View Table 적용
            String viewQuery = queryRequest.viewTable(
                    queryWithOrderBy,
                    parameters,
                    DIALECT
            );
            log.info("View Table 적용 후: {}", viewQuery);

            // 행 수 계산 후 페이지네이션 적용 여부 결정
            // int totalRows = 0;
            // try {
            // String countResult = queryRequest.countRows(sqlQuery, PAGE_SIZE,
            // companyId).block();
            // totalRows = Integer.parseInt(countResult);
            // } catch (NumberFormatException e) {
            // totalRows = 0;
            // }

            // final String effectiveQuery;
            // if (totalRows > PAGE_SIZE) {
            // execution.setExecutionQuery(queryRequest.addLimits(sqlQuery, PAGE_SIZE, 0,
            // supervisorState.getUserInfo()).block());
            // effectiveQuery = execution.getExecutionQuery();
            // } else {
            // execution.setExecutionQuery(sqlQuery);
            // effectiveQuery = sqlQuery;
            // }
            // temp
            log.info("ifExecutor를 사용하여 SQL 실행: {}", viewQuery);

            List<Map<String, Object>> queryResult = ifExecutor.executeIf(
                    viewQuery,
                    supervisorState.getUserInfo().getInttBizNo(),
                    supervisorState.getUserInfo().getInttCntrctId(),
                    FETCH_ALL
            );

            log.info("쿼리 실행 완료. 결과 행 수: {}", queryResult.size());

            // 7. 결과를 ArrowData로 변환하여 execution에 설정
            if (queryResult.isEmpty()) {
                RootAllocator allocator = new RootAllocator();
                ArrowData emptyArrowData = new ArrowData(allocator);
                execution.setExecutionArrowData(emptyArrowData);
            } else {
                ArrowData arrowData = IfExecutor.fromMapList(queryResult);
                execution.setExecutionArrowData(arrowData);
            }

            execution.setExecutionStatus("success");

        } catch (Exception e) {
            log.error("SQL 실행 중 오류 발생: {}", e.getMessage(), e);
            execution.setExecutionError(true);
            execution.setExecutionStatus("error");
            execution.setExecutionErrorMessage("SQL 실행 실패: " + e.getMessage());
        }
    }
}