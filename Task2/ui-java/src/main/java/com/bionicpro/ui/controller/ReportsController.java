package com.bionicpro.ui.controller;

import com.bionicpro.ui.service.ReportsApiService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.client.OAuth2AuthorizedClient;
import org.springframework.security.oauth2.client.annotation.RegisteredOAuth2AuthorizedClient;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.time.LocalDate;

@Slf4j
@Controller
@RequestMapping("/reports")
@RequiredArgsConstructor
public class ReportsController {

    private final ReportsApiService reportsApiService;

    @GetMapping
    public String reports(Authentication authentication, Model model) {
        OAuth2User user = (OAuth2User) authentication.getPrincipal();
        
        model.addAttribute("username", user.getAttribute("preferred_username"));
        model.addAttribute("email", user.getAttribute("email"));
        model.addAttribute("userId", user.getAttribute("sub"));
        
        LocalDate dateTo = LocalDate.now();
        LocalDate dateFrom = dateTo.minusDays(30);
        
        model.addAttribute("dateFrom", dateFrom);
        model.addAttribute("dateTo", dateTo);
        
        return "reports";
    }

    @GetMapping("/data")
    public ResponseEntity<?> getReportData(
            @RegisteredOAuth2AuthorizedClient("keycloak") OAuth2AuthorizedClient authorizedClient,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateFrom,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateTo) {
        
        log.info("Fetching report data from {} to {}", dateFrom, dateTo);
        
        try {
            String accessToken = authorizedClient.getAccessToken().getTokenValue();
            
            String reportData = reportsApiService.getMyReport(accessToken, dateFrom, dateTo);
            
            return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_JSON)
                .body(reportData);
                
        } catch (Exception e) {
            log.error("Error fetching report", e);
            return ResponseEntity.internalServerError()
                .body("{\"error\": \"" + e.getMessage() + "\"}");
        }
    }

    @GetMapping("/download")
    public ResponseEntity<String> downloadReport(
            @RegisteredOAuth2AuthorizedClient("keycloak") OAuth2AuthorizedClient authorizedClient,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateFrom,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateTo) {
        
        log.info("Downloading report from {} to {}", dateFrom, dateTo);
        
        try {
            String accessToken = authorizedClient.getAccessToken().getTokenValue();
            
            String csvData = reportsApiService.getMyReportCsv(accessToken, dateFrom, dateTo);
            
            return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=report.csv")
                .contentType(MediaType.valueOf("text/csv"))
                .body(csvData);
                
        } catch (Exception e) {
            log.error("Error downloading report", e);
            return ResponseEntity.internalServerError()
                .body("Error downloading report: " + e.getMessage());
        }
    }

}


