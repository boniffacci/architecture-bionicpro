package com.bionicpro.reports.service;

import com.bionicpro.reports.model.DailyReport;
import com.bionicpro.reports.model.ReportResponse;
import com.bionicpro.reports.repository.ClickHouseReportRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class ReportService {

    private final ClickHouseReportRepository repository;

    public ReportResponse getUserReport(String userId, LocalDate dateFrom, LocalDate dateTo) {
        log.info("Getting report for user: {}, from: {}, to: {}", userId, dateFrom, dateTo);
        
        validateDateRange(dateFrom, dateTo);
        
        List<DailyReport> dailyReports = repository.findUserReports(userId, dateFrom, dateTo);
        
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

    private void validateDateRange(LocalDate dateFrom, LocalDate dateTo) {
        if (dateFrom.isAfter(dateTo)) {
            throw new IllegalArgumentException("dateFrom cannot be after dateTo");
        }
        
        long daysBetween = java.time.temporal.ChronoUnit.DAYS.between(dateFrom, dateTo);
        if (daysBetween > 90) {
            throw new IllegalArgumentException("Date range cannot exceed 90 days");
        }
    }

}



