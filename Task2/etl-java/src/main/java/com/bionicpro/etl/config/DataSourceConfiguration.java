package com.bionicpro.etl.config;

import com.zaxxer.hikari.HikariDataSource;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.autoconfigure.jdbc.DataSourceProperties;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.jdbc.core.JdbcTemplate;

import javax.sql.DataSource;

/**
 * Конфигурация множественных DataSource для ETL
 * - ClickHouse: целевая OLAP база
 * - Core DB: PostgreSQL источник телеметрии
 */
@Configuration
public class DataSourceConfiguration {

    // ============================================
    // ClickHouse DataSource (Primary)
    // ============================================

    @Bean
    @Primary
    @ConfigurationProperties("spring.datasource.clickhouse")
    public DataSourceProperties clickhouseDataSourceProperties() {
        return new DataSourceProperties();
    }

    @Bean
    @Primary
    @ConfigurationProperties("spring.datasource.clickhouse.configuration")
    public DataSource clickhouseDataSource(@Qualifier("clickhouseDataSourceProperties") DataSourceProperties properties) {
        return properties.initializeDataSourceBuilder()
                .type(HikariDataSource.class)
                .build();
    }

    @Bean
    @Primary
    public JdbcTemplate clickhouseJdbcTemplate(@Qualifier("clickhouseDataSource") DataSource dataSource) {
        return new JdbcTemplate(dataSource);
    }

    // ============================================
    // Core DB DataSource (PostgreSQL)
    // ============================================

    @Bean
    @ConfigurationProperties("spring.datasource.core-db")
    public DataSourceProperties coreDbDataSourceProperties() {
        return new DataSourceProperties();
    }

    @Bean
    @ConfigurationProperties("spring.datasource.core-db.configuration")
    public DataSource coreDbDataSource(@Qualifier("coreDbDataSourceProperties") DataSourceProperties properties) {
        return properties.initializeDataSourceBuilder()
                .type(HikariDataSource.class)
                .build();
    }

    @Bean
    public JdbcTemplate coreDbJdbcTemplate(@Qualifier("coreDbDataSource") DataSource dataSource) {
        return new JdbcTemplate(dataSource);
    }

}



