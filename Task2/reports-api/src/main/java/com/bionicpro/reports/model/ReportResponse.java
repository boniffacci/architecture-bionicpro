package com.bionicpro.reports.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReportResponse {
    
    private String userId;
    
    private LocalDate dateFrom;
    
    private LocalDate dateTo;
    
    private List<DailyReport> dailyReports;
    
    private Integer totalRecords;
    
    private String region;
    
}



