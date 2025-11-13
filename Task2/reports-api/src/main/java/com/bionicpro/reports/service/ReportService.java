package com.bionicpro.reports.service;

import com.bionicpro.reports.model.DailyReport;
import com.bionicpro.reports.model.ReportResponse;
import com.bionicpro.reports.repository.ClickHouseReportRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.List;

/**
 * Сервис для работы с отчётами
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ReportService {

    private final ClickHouseReportRepository repository;

    /**
     * Получить отчёт пользователя за период
     */
    public ReportResponse getUserReport(String userId, LocalDate dateFrom, LocalDate dateTo) {
        log.info("Getting report for user: {}, from: {}, to: {}", userId, dateFrom, dateTo);
        
        // Валидация дат
        validateDateRange(dateFrom, dateTo);
        
        // Получение данных из ClickHouse
        List<DailyReport> dailyReports = repository.findUserReports(userId, dateFrom, dateTo);
        
        // Определение региона (из первой записи, если есть)
        String region = dailyReports.isEmpty() ? null : dailyReports.get(0).getRegion();
        
        return ReportResponse.builder()
            .userId(userId)
            .dateFrom(dateFrom)
            .dateTo(dateTo)
            .dailyReports(dailyReports)
            .totalRecords(dailyReports.size())
            .region(region)
            .build();
    }

    /**
     * Получить отчёт пользователя с фильтром по региону
     */
    public ReportResponse getUserReportByRegion(String userId, LocalDate dateFrom, LocalDate dateTo, String region) {
        log.info("Getting report for user: {}, from: {}, to: {}, region: {}", userId, dateFrom, dateTo, region);
        
        validateDateRange(dateFrom, dateTo);
        
        List<DailyReport> dailyReports = repository.findUserReportsByRegion(userId, dateFrom, dateTo, region);
        
        return ReportResponse.builder()
            .userId(userId)
            .dateFrom(dateFrom)
            .dateTo(dateTo)
            .dailyReports(dailyReports)
            .totalRecords(dailyReports.size())
            .region(region)
            .build();
    }

    /**
     * Валидация диапазона дат
     */
    private void validateDateRange(LocalDate dateFrom, LocalDate dateTo) {
        if (dateFrom.isAfter(dateTo)) {
            throw new IllegalArgumentException("dateFrom cannot be after dateTo");
        }
        
        // Ограничение максимального диапазона (90 дней)
        long daysBetween = java.time.temporal.ChronoUnit.DAYS.between(dateFrom, dateTo);
        if (daysBetween > 90) {
            throw new IllegalArgumentException("Date range cannot exceed 90 days");
        }
    }

}



