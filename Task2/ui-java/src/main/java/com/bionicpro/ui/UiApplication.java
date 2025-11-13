package com.bionicpro.ui;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * BionicPRO UI Application
 * 
 * Spring MVC + Thymeleaf приложение с OAuth2 PKCE аутентификацией.
 * Интегрируется с Keycloak для безопасной аутентификации пользователей
 * и Reports API для получения данных отчётов.
 * 
 * Особенности:
 * - PKCE (Proof Key for Code Exchange) для защиты OAuth2 flow
 * - BFF (Backend for Frontend) паттерн
 * - Изоляция токенов на сервере (не передаются в браузер)
 * - Server-side rendering с Thymeleaf
 */
@SpringBootApplication
public class UiApplication {

    public static void main(String[] args) {
        SpringApplication.run(UiApplication.class, args);
    }

}


