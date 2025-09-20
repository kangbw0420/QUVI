package com.daquv.agent.integration;

import com.daquv.agent.admin.entity.DBConnection;
import com.daquv.agent.admin.entity.DBConnectionType;
import com.daquv.agent.quvi.config.DbConnectionConfig;
import com.daquv.agent.quvi.requests.ColumnRequest;
import com.daquv.agent.quvi.requests.QueryRequest;
import com.daquv.agent.quvi.util.JdbcTemplateResolver;
import com.daquv.agent.quvi.util.BigQueryService;
import com.daquv.agent.workflow.supervisor.SupervisorWorkflowState;
import com.daquv.agent.workflow.util.ArrowData;
import com.google.cloud.bigquery.TableResult;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.ConnectionCallback;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Value;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.ArrayList;
import java.util.Map;
import java.util.Optional;

@Slf4j
@Component
@RequiredArgsConstructor
public class RunSql {

    // private static final int PAGE_SIZE = 100;

    private final JdbcTemplateResolver jdbcTemplateResolver;
    private final ColumnRequest columnRequest;
    private final QueryRequest queryRequest;
    private final NameMappingService nameMappingService;
    private final BigQueryService bigQueryService;
    private final DbConnectionConfig dbConnectionConfig;

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

            log.info("🔌 raw sqlQuery: {}", sqlQuery);

            // 1. 권한 있는 회사 검사
            String queryWithComCondition = columnRequest.addCompanyCondition(sqlQuery, companyId);
            log.info("회사 조건 추가 후: {}", queryWithComCondition);

            Map<String, String> stockMappings = nameMappingService.getStockMappings();
            Map<String, String> bankMappings = nameMappingService.getBankMappings();

            // 2. 주식종목/은행명 매핑 변환
            String queryWithStock = columnRequest.transformStockNames(queryWithComCondition, stockMappings);
            String queryWithBank = columnRequest.transformBankNames(queryWithStock, bankMappings);
            log.info("주식종목/은행명 매핑 후: {}", queryWithBank);

            // 3. orderby clause 추가
            String queryWithOrderBy = queryRequest.addOrderBy(sqlQuery);
            log.info("🔌 queryWithOrderBy: {}", queryWithOrderBy);

            // 4. view_table 파라미터 준비
            // UserInfo 안에서 use_intt_id, user_id, company_id를 뽑아 parameters에 넣어야 함
            List<String> parameterFromUserInfo = new ArrayList<>();
            parameterFromUserInfo.add(supervisorState.getUserInfo().getUseInttId());
            parameterFromUserInfo.add(supervisorState.getUserInfo().getUserId());
            parameterFromUserInfo.add(supervisorState.getUserInfo().getCompanyId());
            List<String> parameters = new ArrayList<>(parameterFromUserInfo);

            parameters.add(execution.getExecutionStartDate());
            parameters.add(execution.getExecutionEndDate());

            String viewQuery = queryRequest.viewTable(
                    queryWithOrderBy,
                    parameters,
                    DIALECT);
            log.info("🔌 viewQuery: {}", viewQuery);

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
            // String effectiveQuery = viewQuery;
            String effectiveQuery = queryWithOrderBy;

            // DbConnectionConfig를 사용하여 DB 연결 해결
            // Entity 정보는 executionDsl.groupBy에서 추출
            List<String> groupByFields = null;
            if (execution.getExecutionDsl() != null && execution.getExecutionDsl().getGroupBy() != null) {
                groupByFields = execution.getExecutionDsl().getGroupBy();
            }

            Optional<DBConnection> dbConnectionOpt = dbConnectionConfig.resolveDbConnectionByEntity(companyId,
                    groupByFields);
            if (dbConnectionOpt.isPresent()) {
                DBConnection dbConnection = dbConnectionOpt.get();

                if (dbConnection.getDbType() == DBConnectionType.BIGQUERY) {
                    // BigQuery 처리
                    TableResult tableResult = bigQueryService.executeQuery(companyId, effectiveQuery);
                    ArrowData arrowData = ArrowData.fromTableResult(tableResult);
                    execution.setExecutionArrowData(arrowData);
                    return;
                } else {
                    // 일반 DB 처리 - 결정된 DB 연결 사용
                    log.info("🔌 Entity 기반 DB 연결 사용 - 연결 ID: {}, 타입: {}, 호스트: {}:{}",
                            dbConnection.getId(), dbConnection.getDbType(),
                            dbConnection.getHost(), dbConnection.getPort());

                    JdbcTemplate jdbcTemplate = jdbcTemplateResolver.getJdbcTemplateByConnection(dbConnection);
                    ArrowData arrowData = jdbcTemplate.execute((ConnectionCallback<ArrowData>) connection -> {
                        try (java.sql.PreparedStatement stmt = connection.prepareStatement(
                                effectiveQuery,
                                ResultSet.TYPE_SCROLL_INSENSITIVE,
                                ResultSet.CONCUR_READ_ONLY);
                                ResultSet rs = stmt.executeQuery()) {
                            return ArrowData.fromResultSet(rs);
                        } catch (SQLException e) {
                            throw new RuntimeException("Arrow 데이터 생성 실패", e);
                        }
                    });
                    execution.setExecutionArrowData(arrowData);
                    return;
                }
            } else {
                // Fallback: 기존 방식 (companyId 기반)
                log.info("🔌 Entity 기반 연결 실패, companyId 기반 연결 사용: {}", companyId);

                // Cross-database 참조 제거
                String sqlWithoutDbname = removeCrossDatabaseReferences(effectiveQuery);

                JdbcTemplate jdbcTemplate = jdbcTemplateResolver.getJdbcTemplate(companyId);
                ArrowData arrowData = jdbcTemplate.execute((ConnectionCallback<ArrowData>) connection -> {
                    try (java.sql.PreparedStatement stmt = connection.prepareStatement(
                            sqlWithoutDbname,
                            ResultSet.TYPE_SCROLL_INSENSITIVE,
                            ResultSet.CONCUR_READ_ONLY);
                            ResultSet rs = stmt.executeQuery()) {
                        return ArrowData.fromResultSet(rs);
                    } catch (SQLException e) {
                        throw new RuntimeException("Arrow 데이터 생성 실패", e);
                    }
                });
                execution.setExecutionArrowData(arrowData);
            }

        } catch (DataAccessException e) {
            // Cross-database 오류 처리: 참조 제거 후 재시도
            try {
                String fixed = fixCrossDatabaseReferences(sqlQuery);
                String companyId = supervisorState.getUserInfo().getCompanyId();
                JdbcTemplate retryJdbc = jdbcTemplateResolver.getJdbcTemplate(companyId);
                ArrowData retryData = retryJdbc.execute((ConnectionCallback<ArrowData>) connection -> {
                    String q = fixed;
                    try (java.sql.PreparedStatement stmt = connection.prepareStatement(
                            q,
                            ResultSet.TYPE_SCROLL_INSENSITIVE,
                            ResultSet.CONCUR_READ_ONLY);
                            ResultSet rs = stmt.executeQuery()) {
                        return ArrowData.fromResultSet(rs);
                    } catch (SQLException ex) {
                        throw new RuntimeException("Arrow 데이터 생성 실패", ex);
                    }
                });
                execution.setExecutionArrowData(retryData);
            } catch (Exception retryEx) {
                execution.setExecutionError(true);
                execution.setExecutionStatus("error");
                execution.setExecutionErrorMessage("SQL 실행 실패: " + e.getMessage());

                // 사용자에게 전달할 에러 메시지 설정
                String errorMessage = "SQL 실행 중 오류가 발생했습니다: " + retryEx.getMessage();
                supervisorState.setFinalAnswer(errorMessage);

                throw retryEx;
            }
        } catch (Exception e) {
            execution.setExecutionError(true);
            execution.setExecutionStatus("error");
            execution.setExecutionErrorMessage("SQL 실행 실패: " + e.getMessage());

            // 사용자에게 전달할 에러 메시지 설정
            String errorMessage = "SQL 실행 중 오류가 발생했습니다: " + e.getMessage();
            supervisorState.setFinalAnswer(errorMessage);

            throw e;
        }
    }

    private String removeCrossDatabaseReferences(String sql) {
        if (sql == null)
            return sql;
        return sql.replaceAll("\\b[a-zA-Z_][a-zA-Z0-9_]*\\.([a-zA-Z_][a-zA-Z0-9_]*)\\.([a-zA-Z_][a-zA-Z0-9_]*)",
                "$1.$2");
    }

    private String fixCrossDatabaseReferences(String sql) {
        if (sql == null)
            return sql;
        String fixedSql = sql;
        fixedSql = fixedSql.replaceAll("\"[^\"]+\"\\.\"([^\"]+)\"\\.\"([^\"]+)\"", "\"$1\".\"$2\"");
        fixedSql = fixedSql
                .replaceAll("\\b[a-zA-Z_][a-zA-Z0-9_]*\\.([a-zA-Z_][a-zA-Z0-9_]*)\\.([a-zA-Z_][a-zA-Z0-9_]*)", "$1.$2");
        fixedSql = fixedSql.replaceAll("\\b[a-zA-Z_][a-zA-Z0-9_]*\\.\"([^\"]+)\"\\.\"([^\"]+)\"", "\"$1\".\"$2\"");
        fixedSql = fixedSql.replaceAll("\"[^\"]+\"\\.([a-zA-Z_][a-zA-Z0-9_]*)\\.([a-zA-Z_][a-zA-Z0-9_]*)", "$1.$2");
        return fixedSql;
    }
}
