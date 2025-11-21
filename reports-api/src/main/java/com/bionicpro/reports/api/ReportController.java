package com.bionicpro.reports.api;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.sql.DataSource;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@RestController
public class ReportController {
    private final JdbcTemplate jdbcTemplate;

    private static final Logger log = LoggerFactory.getLogger(ReportController.class);

    public ReportController(DataSource dataSource) {
        this.jdbcTemplate = new JdbcTemplate(dataSource);
    }

    @GetMapping("/reports")
    public ResponseEntity<?> getReport(@AuthenticationPrincipal Jwt jwt) {
        log.info("JWT claims: {}", jwt.getClaims());
        System.out.println("Controller: Get email");
        String email = jwt.getClaim("email");
        System.out.println("Controller: email = " + email);
        if (email == null) {
            System.out.println("Controller: email is null");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }

        String sql = "SELECT * FROM default.customer_emg_analytics WHERE email = ?";
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(sql, email);

        return ResponseEntity.ok(rows);
    }
}
