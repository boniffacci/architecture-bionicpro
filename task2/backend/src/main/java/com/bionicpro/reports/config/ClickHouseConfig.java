package com.bionicpro.reports.config;

import com.clickhouse.jdbc.ClickHouseDataSource;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;

import javax.sql.DataSource;
import java.sql.SQLException;
import java.util.Properties;

@Configuration
public class ClickHouseConfig {

    @Value("${clickhouse.url:jdbc:clickhouse://localhost:8123/bionicpro_reports}")
    private String clickhouseUrl;

    @Value("${clickhouse.user:default}")
    private String clickhouseUser;

    @Value("${clickhouse.password:}")
    private String clickhousePassword;

    @Bean
    public DataSource clickHouseDataSource() throws SQLException {
        Properties properties = new Properties();
        properties.setProperty("user", clickhouseUser);
        if (clickhousePassword != null && !clickhousePassword.isEmpty()) {
            properties.setProperty("password", clickhousePassword);
        }
        
        return new ClickHouseDataSource(clickhouseUrl, properties);
    }

    @Bean
    public JdbcTemplate jdbcTemplate(DataSource clickHouseDataSource) {
        return new JdbcTemplate(clickHouseDataSource);
    }
}

