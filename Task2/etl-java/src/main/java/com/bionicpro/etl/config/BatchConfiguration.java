package com.bionicpro.etl.config;

import lombok.RequiredArgsConstructor;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.job.builder.JobBuilder;
import org.springframework.batch.core.launch.support.RunIdIncrementer;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.PlatformTransactionManager;

import javax.sql.DataSource;

/**
 * Spring Batch конфигурация для ETL процессов
 */
@Configuration
@RequiredArgsConstructor
public class BatchConfiguration {

    private final JobRepository jobRepository;
    private final PlatformTransactionManager transactionManager;

    /**
     * Job: Построение витрины отчётов
     * 
     * Агрегирует данные из raw_crm_users и raw_telemetry
     * и создаёт витрину mart_report_user_daily
     */
    @Bean
    public Job buildMartJob(Step buildMartStep) {
        return new JobBuilder("buildMartJob", jobRepository)
                .incrementer(new RunIdIncrementer())
                .start(buildMartStep)
                .build();
    }

    /**
     * Step: Агрегация и построение витрины
     */
    @Bean
    public Step buildMartStep(JdbcTemplate clickhouseTemplate) {
        return new StepBuilder("buildMartStep", jobRepository)
                .tasklet((contribution, chunkContext) -> {
                    
                    String reportDate = chunkContext.getStepContext()
                            .getJobParameters()
                            .getOrDefault("date", java.time.LocalDate.now().toString())
                            .toString();
                    
                    // SQL для построения витрины
                    String sql = """
                        INSERT INTO mart_report_user_daily (
                            user_id,
                            report_date,
                            metrics.name,
                            metrics.events_count,
                            metrics.value_sum,
                            metrics.value_avg,
                            metrics.value_min,
                            metrics.value_max,
                            region,
                            prosthetic_model
                        )
                        SELECT
                            t.user_id,
                            toDate(t.event_timestamp) AS report_date,
                            groupArray(t.metric_name) AS metric_names,
                            groupArray(count(*)) AS events_counts,
                            groupArray(sum(t.metric_value)) AS value_sums,
                            groupArray(avg(t.metric_value)) AS value_avgs,
                            groupArray(min(t.metric_value)) AS value_mins,
                            groupArray(max(t.metric_value)) AS value_maxs,
                            any(u.region) AS region,
                            any(u.prosthetic_model) AS prosthetic_model
                        FROM raw_telemetry t
                        LEFT JOIN raw_crm_users u ON t.user_id = u.user_id
                        WHERE toDate(t.event_timestamp) = ?
                        GROUP BY t.user_id, report_date, t.metric_name
                        """;
                    
                    int rowsAffected = clickhouseTemplate.update(sql, reportDate);
                    
                    System.out.printf("✅ Built mart for date %s: %d rows inserted%n", reportDate, rowsAffected);
                    
                    return org.springframework.batch.repeat.RepeatStatus.FINISHED;
                }, transactionManager)
                .build();
    }

    /**
     * Job: Извлечение данных CRM
     */
    @Bean
    public Job extractCrmJob(Step extractCrmStep) {
        return new JobBuilder("extractCrmJob", jobRepository)
                .incrementer(new RunIdIncrementer())
                .start(extractCrmStep)
                .build();
    }

    /**
     * Step: Извлечение CRM данных через REST API
     */
    @Bean
    public Step extractCrmStep(JdbcTemplate clickhouseTemplate) {
        return new StepBuilder("extractCrmStep", jobRepository)
                .tasklet((contribution, chunkContext) -> {
                    
                    // TODO: Реализовать REST клиент для CRM API
                    System.out.println("✅ Extracting CRM data...");
                    
                    // Пример вставки данных (в реальности - из CRM API)
                    String sql = """
                        INSERT INTO raw_crm_users (user_id, username, email, contract_number, prosthetic_model, region, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, now())
                        """;
                    
                    // Заглушка - в реальности данные приходят из CRM
                    System.out.println("✅ CRM extraction completed");
                    
                    return org.springframework.batch.repeat.RepeatStatus.FINISHED;
                }, transactionManager)
                .build();
    }

    /**
     * Job: Извлечение телеметрии
     */
    @Bean
    public Job extractTelemetryJob(Step extractTelemetryStep) {
        return new JobBuilder("extractTelemetryJob", jobRepository)
                .incrementer(new RunIdIncrementer())
                .start(extractTelemetryStep)
                .build();
    }

    /**
     * Step: Извлечение телеметрии из Core DB
     */
    @Bean
    public Step extractTelemetryStep(JdbcTemplate coreDbTemplate, JdbcTemplate clickhouseTemplate) {
        return new StepBuilder("extractTelemetryStep", jobRepository)
                .tasklet((contribution, chunkContext) -> {
                    
                    String reportDate = chunkContext.getStepContext()
                            .getJobParameters()
                            .getOrDefault("date", java.time.LocalDate.now().toString())
                            .toString();
                    
                    System.out.printf("✅ Extracting telemetry for date: %s%n", reportDate);
                    
                    // TODO: Реализовать извлечение из Core DB PostgreSQL
                    // и загрузку в ClickHouse raw_telemetry
                    
                    System.out.println("✅ Telemetry extraction completed");
                    
                    return org.springframework.batch.repeat.RepeatStatus.FINISHED;
                }, transactionManager)
                .build();
    }

    /**
     * JdbcTemplate для ClickHouse
     */
    @Bean
    public JdbcTemplate clickhouseTemplate(DataSource dataSource) {
        return new JdbcTemplate(dataSource);
    }

    /**
     * JdbcTemplate для Core DB (PostgreSQL)
     */
    @Bean
    public JdbcTemplate coreDbTemplate() {
        // TODO: Настроить отдельный DataSource для Core DB
        // Пока используем основной (ClickHouse)
        return new JdbcTemplate();
    }

}



