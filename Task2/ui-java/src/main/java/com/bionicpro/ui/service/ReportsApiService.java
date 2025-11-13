package com.bionicpro.ui.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.LocalDate;

/**
 * Сервис для взаимодействия с BionicPRO Reports API
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ReportsApiService {

    private final WebClient.Builder webClientBuilder;

    @Value("${bionicpro.api.base-url}")
    private String apiBaseUrl;

    /**
     * Получить отчёт пользователя в JSON формате
     */
    public String getMyReport(String accessToken, LocalDate dateFrom, LocalDate dateTo) {
        log.debug("Calling Reports API: GET /reports/me");
        
        WebClient webClient = webClientBuilder
            .baseUrl(apiBaseUrl)
            .defaultHeader("Authorization", "Bearer " + accessToken)
            .build();
        
        return webClient.get()
            .uri(uriBuilder -> uriBuilder
                .path("/reports/me")
                .queryParam("dateFrom", dateFrom.toString())
                .queryParam("dateTo", dateTo.toString())
                .queryParam("format", "json")
                .build())
            .retrieve()
            .bodyToMono(String.class)
            .block();
    }

    /**
     * Получить отчёт пользователя в CSV формате
     */
    public String getMyReportCsv(String accessToken, LocalDate dateFrom, LocalDate dateTo) {
        log.debug("Calling Reports API: GET /reports/me (CSV format)");
        
        WebClient webClient = webClientBuilder
            .baseUrl(apiBaseUrl)
            .defaultHeader("Authorization", "Bearer " + accessToken)
            .build();
        
        return webClient.get()
            .uri(uriBuilder -> uriBuilder
                .path("/reports/me")
                .queryParam("dateFrom", dateFrom.toString())
                .queryParam("dateTo", dateTo.toString())
                .queryParam("format", "csv")
                .build())
            .retrieve()
            .bodyToMono(String.class)
            .block();
    }

}


