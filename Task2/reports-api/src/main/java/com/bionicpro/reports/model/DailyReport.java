package com.bionicpro.reports.model;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

/**
 * Дневной отчёт пользователя
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DailyReport {
    
    /** ID пользователя */
    private String userId;
    
    /** Дата отчёта */
    @JsonFormat(pattern = "yyyy-MM-dd")
    private LocalDate reportDate;
    
    /** Список метрик */
    private List<MetricData> metrics;
    
    /** Регион пользователя */
    private String region;
    
    /** Модель протеза */
    private String prostheticModel;
    
    /** Время генерации отчёта */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime generatedAt;
    
}



