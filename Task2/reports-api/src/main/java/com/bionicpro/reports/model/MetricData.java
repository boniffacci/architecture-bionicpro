package com.bionicpro.reports.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MetricData {
    
    private String name;
    
    private Long eventsCount;
    
    private Double valueSum;
    
    private Double valueAvg;
    
    private Double valueMin;
    
    private Double valueMax;
    
}



