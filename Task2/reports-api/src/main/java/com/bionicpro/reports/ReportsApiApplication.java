package com.bionicpro.reports;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

/**
 * BionicPRO Reports API Application
 * 
 * REST API для получения отчётов о работе протезов пользователей.
 * Читает агрегированные данные из ClickHouse и предоставляет их через REST endpoints.
 * 
 * Безопасность: OAuth2 Resource Server с валидацией JWT от Keycloak
 */
@SpringBootApplication
@ConfigurationPropertiesScan
public class ReportsApiApplication {

    public static void main(String[] args) {
        SpringApplication.run(ReportsApiApplication.class, args);
    }

}



