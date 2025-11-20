package com.bionicpro.reports.model;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DailyReport {
    
    private String userId;
    
    @JsonFormat(pattern = "yyyy-MM-dd")
    private LocalDate reportDate;
    
    private List<MetricData> metrics;
    
    private String region;
    
    private String prostheticModel;
    
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime generatedAt;
    
}



