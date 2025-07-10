package com.daquv.agent.config;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.jdbc.core.JdbcTemplate;

import javax.sql.DataSource;


@Configuration
public class DatabaseConfig {

    // Main DB (GenerateService용)
    @Value("${db.url}")
    private String mainDbUrl;

    @Value("${db.username}")
    private String mainDbUsername;

    @Value("${db.password}")
    private String mainDbPassword;

    @Value("${db.driver-class-name}")
    private String mainDbDriver;

    // Prompt DB (JPA 엔티티용) - slp_admin
    @Value("${spring.datasource.driver-class-name}")
    private String promptDbDriver;

    @Value("${spring.datasource.url}")
    private String promptDbUrl;

    @Value("${spring.datasource.username}")
    private String promptDbUsername;

    @Value("${spring.datasource.password}")
    private String promptDbPassword;

    @Value("${spring.datasource.hikari.schema}")
    private String promptDbSchema;

    @Bean(name = "mainDataSource")
    public DataSource mainDataSource() {
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl(mainDbUrl);
        config.setUsername(mainDbUsername);
        config.setPassword(mainDbPassword);
        config.setDriverClassName(mainDbDriver);

        // 커넥션 풀 설정
        config.setMaximumPoolSize(20); // 최대 커넥션 수
        config.setMinimumIdle(5); // 최소 유지 커넥션 수
        config.setConnectionTimeout(30000); // 커넥션 획득 타임아웃 (30초)
        config.setIdleTimeout(600000); // 유휴 커넥션 타임아웃 (10분)
        config.setMaxLifetime(1800000); // 커넥션 최대 생존 시간 (30분)
        config.setLeakDetectionThreshold(60000); // 커넥션 누수 감지 (1분)

        // 커넥션 검증
        config.setConnectionTestQuery("SELECT 1");
        config.setValidationTimeout(5000); // 검증 타임아웃 (5초)

        // 풀 이름 설정 (모니터링용)
        config.setPoolName("MainDB-Pool");

        return new HikariDataSource(config);
    }

    @Primary
    @Bean(name = "promptDataSource")
    public DataSource promptDataSource() {
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl(promptDbUrl + "?currentSchema=" + promptDbSchema);
        config.setUsername(promptDbUsername);
        config.setPassword(promptDbPassword);
        config.setDriverClassName(promptDbDriver);

        // 커넥션 풀 설정 (JPA용이므로 좀 더 여유있게)
        config.setMaximumPoolSize(15);
        config.setMinimumIdle(3);
        config.setConnectionTimeout(30000);
        config.setIdleTimeout(600000);
        config.setMaxLifetime(1800000);
        config.setLeakDetectionThreshold(60000);

        // 커넥션 검증
        config.setConnectionTestQuery("SELECT 1");
        config.setValidationTimeout(5000);

        // 풀 이름 설정
        config.setPoolName("PromptDB-Pool");

        return new HikariDataSource(config);
    }

    @Bean(name = "mainJdbcTemplate")
    public JdbcTemplate mainJdbcTemplate(@Qualifier("mainDataSource") DataSource dataSource) {
        JdbcTemplate jdbcTemplate = new JdbcTemplate(dataSource);
        jdbcTemplate.setQueryTimeout(30); // 기본 쿼리 타임아웃 30초
        return jdbcTemplate;
    }

    @Primary
    @Bean(name = "promptJdbcTemplate")
    public JdbcTemplate promptJdbcTemplate(@Qualifier("promptDataSource") DataSource dataSource) {
        JdbcTemplate jdbcTemplate = new JdbcTemplate(dataSource);
        jdbcTemplate.setQueryTimeout(30);
        return jdbcTemplate;
    }
}