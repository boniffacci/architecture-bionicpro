package com.example.spring_boot;

import org.springframework.core.io.InputStreamResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

@RestController
public class ReportController {

    @GetMapping(value = "/reports", produces = MediaType.TEXT_PLAIN_VALUE)
    public ResponseEntity<InputStreamResource> generateReport(@AuthenticationPrincipal Jwt jwt) {

        // Generate random string (using UUID as example)
        String randomString = "Report data: " + UUID.randomUUID().toString();

        // Create input stream from the string
        ByteArrayInputStream reportStream = new ByteArrayInputStream(
                randomString.getBytes(StandardCharsets.UTF_8));

        // Set headers for file download
        HttpHeaders headers = new HttpHeaders();
        headers.add(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=report.txt");

        return ResponseEntity.ok()
                .headers(headers)
                .contentType(MediaType.TEXT_PLAIN)
                .body(new InputStreamResource(reportStream));
    }
}
