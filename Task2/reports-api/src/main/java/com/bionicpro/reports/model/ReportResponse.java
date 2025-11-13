package com.bionicpro.reports.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.List;

/**
 * Response DTO для API отчётов
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReportResponse {
    
    /** ID пользователя */
    private String userId;
    
    /** Дата начала периода */
    private LocalDate dateFrom;
    
    /** Дата конца периода */
    private LocalDate dateTo;
    
    /** Список дневных отчётов */
    private List<DailyReport> dailyReports;
    
    /** Общее количество записей */
    private Integer totalRecords;
    
    /** Регион пользователя */
    private String region;
    
}



