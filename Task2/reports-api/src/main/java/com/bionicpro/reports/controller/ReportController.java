package com.bionicpro.reports.controller;

import com.bionicpro.reports.model.ReportResponse;
import com.bionicpro.reports.service.ReportService;
import com.bionicpro.reports.util.CsvUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;

/**
 * REST контроллер для работы с отчётами
 */
@Slf4j
@RestController
@RequestMapping("/reports")
@RequiredArgsConstructor
public class ReportController {

    private final ReportService reportService;

    /**
     * Получить отчёт текущего пользователя
     * 
     * GET /api/reports/me?dateFrom=2024-01-01&dateTo=2024-01-31&format=json
     */
    @GetMapping("/me")
    public ResponseEntity<?> getMyReport(
            @AuthenticationPrincipal Jwt jwt,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateFrom,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateTo,
            @RequestParam(defaultValue = "json") String format) {
        
        // Извлечение user_id из JWT subject claim
        String userId = jwt.getSubject();
        log.info("User {} requested report from {} to {} in format {}", userId, dateFrom, dateTo, format);
        
        // Получение отчёта
        ReportResponse report = reportService.getUserReport(userId, dateFrom, dateTo);
        
        // Форматирование ответа
        if ("csv".equalsIgnoreCase(format)) {
            return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=report.csv")
                .contentType(MediaType.valueOf("text/csv"))
                .body(CsvUtil.toCsv(report));
        }
        
        return ResponseEntity.ok()
            .contentType(MediaType.APPLICATION_JSON)
            .body(report);
    }

    /**
     * Получить отчёт любого пользователя (только для администраторов)
     * 
     * GET /api/reports?userId=user-001&dateFrom=2024-01-01&dateTo=2024-01-31
     */
    @GetMapping
    public ResponseEntity<ReportResponse> getReport(
            @AuthenticationPrincipal Jwt jwt,
            @RequestParam String userId,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateFrom,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateTo,
            @RequestParam(required = false) String region) {
        
        log.info("Admin {} requested report for user {} from {} to {}", 
            jwt.getSubject(), userId, dateFrom, dateTo);
        
        ReportResponse report;
        if (region != null) {
            report = reportService.getUserReportByRegion(userId, dateFrom, dateTo, region);
        } else {
            report = reportService.getUserReport(userId, dateFrom, dateTo);
        }
        
        return ResponseEntity.ok(report);
    }

    /**
     * Health check endpoint
     */
    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("Reports API is running");
    }

}



