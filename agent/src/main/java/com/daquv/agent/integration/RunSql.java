package com.daquv.agent.integration;

import com.daquv.agent.admin.entity.DBConnection;
import com.daquv.agent.admin.entity.DBConnectionType;
import com.daquv.agent.quvi.admin.DbConnectionService;
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

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Optional;

@Slf4j
@Component
@RequiredArgsConstructor
public class RunSql {

    private static final int PAGE_SIZE = 100;

    private final JdbcTemplateResolver jdbcTemplateResolver;
    private final QueryRequest queryRequest;
    private final BigQueryService bigQueryService;
    private final DbConnectionService dbConnectionService;

    /**
     * SQL을 실행하고 결과를 execution에 채워 넣는다.
     */
    public void executeSqlAndFillExecution(String sqlQuery,
                                            SupervisorWorkflowState supervisorState,
                                            SupervisorWorkflowState.WorkflowExecution execution) {
        try {
            String companyId = supervisorState.getUserInfo().getCompanyId();

            // 행 수 계산 후 페이지네이션 적용 여부 결정
            int totalRows = 0;
            try {
                String countResult = queryRequest.countRows(sqlQuery, PAGE_SIZE, companyId).block();
                totalRows = Integer.parseInt(countResult);
            } catch (NumberFormatException e) {
                totalRows = 0;
            }

            String effectiveQuery = sqlQuery;
            if (totalRows > PAGE_SIZE) {
                execution.setExecutionQuery(queryRequest.addLimits(sqlQuery, PAGE_SIZE, 0, supervisorState.getUserInfo()).block());
                effectiveQuery = execution.getExecutionQuery();
            } else {
                execution.setExecutionQuery(sqlQuery);
            }

            // DB 타입 확인하여 BigQuery면 전용 경로 사용
            Optional<DBConnection> dbConnectionOpt = dbConnectionService.getDbConnectionByCompanyId(companyId);
            if (dbConnectionOpt.isPresent() && dbConnectionOpt.get().getDbType() == DBConnectionType.BIGQUERY) {
                TableResult tableResult = bigQueryService.executeQuery(companyId, effectiveQuery);
                ArrowData arrowData = ArrowData.fromTableResult(tableResult);
                execution.setExecutionArrowData(arrowData);
                return;
            }

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
            }
        } catch (Exception e) {
            execution.setExecutionError(true);
            execution.setExecutionStatus("error");
            execution.setExecutionErrorMessage("SQL 실행 실패: " + e.getMessage());
        }
    }

    private String removeCrossDatabaseReferences(String sql) {
        if (sql == null) return sql;
        return sql.replaceAll("\\b[a-zA-Z_][a-zA-Z0-9_]*\\.([a-zA-Z_][a-zA-Z0-9_]*)\\.([a-zA-Z_][a-zA-Z0-9_]*)", "$1.$2");
    }

    private String fixCrossDatabaseReferences(String sql) {
        if (sql == null) return sql;
        String fixedSql = sql;
        fixedSql = fixedSql.replaceAll("\"[^\"]+\"\\.\"([^\"]+)\"\\.\"([^\"]+)\"", "\"$1\".\"$2\"");
        fixedSql = fixedSql.replaceAll("\\b[a-zA-Z_][a-zA-Z0-9_]*\\.([a-zA-Z_][a-zA-Z0-9_]*)\\.([a-zA-Z_][a-zA-Z0-9_]*)", "$1.$2");
        fixedSql = fixedSql.replaceAll("\\b[a-zA-Z_][a-zA-Z0-9_]*\\.\"([^\"]+)\"\\.\"([^\"]+)\"", "\"$1\".\"$2\"");
        fixedSql = fixedSql.replaceAll("\"[^\"]+\"\\.([a-zA-Z_][a-zA-Z0-9_]*)\\.([a-zA-Z_][a-zA-Z0-9_]*)", "$1.$2");
        return fixedSql;
    }
}


