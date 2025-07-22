package com.daquv.agent.quvi.entity;

import lombok.AccessLevel;
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;
import lombok.experimental.SuperBuilder;

import javax.persistence.*;

@MappedSuperclass
@Getter
@Setter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@SuperBuilder
public abstract class BaseState {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    protected Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "node_id", nullable = false)
    protected Node node;

    @Column(name = "user_question", columnDefinition = "TEXT")
    protected String userQuestion;

    @Column(name = "selected_table")
    protected String selectedTable;

    @Column(name = "sql_query", columnDefinition = "TEXT")
    protected String sqlQuery;

    @Column(name = "query_result", columnDefinition = "TEXT")
    protected String queryResult;

    @Column(name = "final_answer", columnDefinition = "TEXT")
    protected String finalAnswer;

    @Column(name = "company_id", length = 100)
    protected String companyId;

    @Column(name = "sql_error", columnDefinition = "TEXT")
    protected String sqlError;

    @Column(name = "start_date", length = 6)
    protected String startDate;

    @Column(name = "end_date", length = 6)
    protected String endDate;

    @Column(name = "selected_api")
    protected String selectedApi;

    @Column(name = "fstring_answer", columnDefinition = "TEXT")
    protected String fstringAnswer;

    @Column(name = "total_rows")
    protected Integer totalRows;



    /**
     * 상태 정보 업데이트
     */
    public void updateState(String userQuestion, String selectedTable, String sqlQuery,
                            String queryResult, String finalAnswer, String companyId) {
        this.userQuestion = userQuestion;
        this.selectedTable = selectedTable;
        this.sqlQuery = sqlQuery;
        this.queryResult = queryResult;
        this.finalAnswer = finalAnswer;
        this.companyId = companyId;
    }

    /**
     * SQL 에러 설정
     */
    public void setSqlError(String sqlError) {
        this.sqlError = sqlError;
    }

    /**
     * 결과 행 수 설정
     */
    public void setTotalRows(Integer totalRows) {
        this.totalRows = totalRows;
    }
}