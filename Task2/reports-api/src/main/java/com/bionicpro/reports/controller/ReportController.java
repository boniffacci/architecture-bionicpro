package com.bionicpro.reports.controller;

import com.bionicpro.reports.model.ReportResponse;
import com.bionicpro.reports.service.ReportService;
import com.bionicpro.reports.util.CsvUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;

@Slf4j
@RestController
@RequestMapping("/reports")
@RequiredArgsConstructor
public class ReportController {

    private final ReportService reportService;

    @GetMapping("/me")
    public ResponseEntity<?> getMyReport(
            @AuthenticationPrincipal Jwt jwt,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateFrom,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateTo,
            @RequestParam(defaultValue = "json") String format) {
        
        String userId = jwt.getSubject();
        log.info("User {} requested report from {} to {} in format {}", userId, dateFrom, dateTo, format);
        
        ReportResponse report = reportService.getUserReport(userId, dateFrom, dateTo);
        
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

    @GetMapping
    @PreAuthorize("hasRole('ADMINISTRATOR')")
    public ResponseEntity<ReportResponse> getReport(
            @AuthenticationPrincipal Jwt jwt,
            Authentication authentication,
            @RequestParam String userId,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateFrom,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateTo,
            @RequestParam(required = false) String region) {
        
        log.info("Admin {} (authorities: {}) requested report for user {} from {} to {}", 
            jwt.getSubject(),
            authentication.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .collect(java.util.stream.Collectors.joining(", ")),
            userId, dateFrom, dateTo);
        
        ReportResponse report;
        if (region != null) {
            report = reportService.getUserReportByRegion(userId, dateFrom, dateTo, region);
        } else {
            report = reportService.getUserReport(userId, dateFrom, dateTo);
        }
        
        return ResponseEntity.ok(report);
    }

    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("Reports API is running");
    }

}



