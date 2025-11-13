package com.bionicpro.reports.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Данные метрики пользователя
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MetricData {
    
    /** Название метрики (steps, battery_level, motion_quality и т.д.) */
    private String name;
    
    /** Количество событий */
    private Long eventsCount;
    
    /** Сумма значений */
    private Double valueSum;
    
    /** Среднее значение */
    private Double valueAvg;
    
    /** Минимальное значение */
    private Double valueMin;
    
    /** Максимальное значение */
    private Double valueMax;
    
}



