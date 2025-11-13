package com.bionicpro.ui.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.oauth2.client.registration.ClientRegistrationRepository;
import org.springframework.security.oauth2.client.web.DefaultOAuth2AuthorizationRequestResolver;
import org.springframework.security.oauth2.client.web.OAuth2AuthorizationRequestResolver;
import org.springframework.security.oauth2.core.endpoint.OAuth2AuthorizationRequest;
import org.springframework.security.web.SecurityFilterChain;

import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.function.Consumer;

/**
 * Spring Security конфигурация с OAuth2 PKCE
 * 
 * PKCE (Proof Key for Code Exchange) - RFC 7636
 * Защищает Authorization Code Flow от атак перехвата кода
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    /**
     * Основная конфигурация безопасности
     */
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http,
                                          OAuth2AuthorizationRequestResolver pkceResolver) throws Exception {
        http
            .authorizeHttpRequests(authz -> authz
                // Публичные endpoints
                .requestMatchers("/", "/login", "/error", "/css/**", "/js/**", "/images/**").permitAll()
                .requestMatchers("/actuator/health").permitAll()
                
                // Все остальные требуют аутентификации
                .anyRequest().authenticated())
            
            // OAuth2 Login с PKCE
            .oauth2Login(oauth2 -> oauth2
                .loginPage("/login")
                .defaultSuccessUrl("/reports", true)
                .authorizationEndpoint(authorization -> authorization
                    .authorizationRequestResolver(pkceResolver)))
            
            // Logout
            .logout(logout -> logout
                .logoutUrl("/logout")
                .logoutSuccessUrl("/")
                .invalidateHttpSession(true)
                .deleteCookies("JSESSIONID"));
        
        return http.build();
    }

    /**
     * OAuth2 Authorization Request Resolver с PKCE
     * 
     * Автоматически добавляет PKCE параметры:
     * - code_challenge
     * - code_challenge_method=S256
     */
    @Bean
    public OAuth2AuthorizationRequestResolver pkceResolver(
            ClientRegistrationRepository clientRegistrationRepository) {
        
        DefaultOAuth2AuthorizationRequestResolver defaultResolver =
            new DefaultOAuth2AuthorizationRequestResolver(
                clientRegistrationRepository, "/oauth2/authorization");
        
        // Customize resolver to add PKCE parameters
        defaultResolver.setAuthorizationRequestCustomizer(
            authorizationRequestCustomizer());
        
        return defaultResolver;
    }

    /**
     * Customizer для добавления PKCE параметров
     */
    private Consumer<OAuth2AuthorizationRequest.Builder> authorizationRequestCustomizer() {
        return builder -> {
            // Генерация code_verifier
            String codeVerifier = generateCodeVerifier();
            
            // Генерация code_challenge = BASE64URL(SHA256(code_verifier))
            String codeChallenge = generateCodeChallenge(codeVerifier);
            
            // Добавляем PKCE параметры в запрос
            builder
                .additionalParameters(params -> {
                    params.put("code_challenge", codeChallenge);
                    params.put("code_challenge_method", "S256");
                })
                // Сохраняем code_verifier в атрибутах для последующего использования
                .attributes(attrs -> {
                    attrs.put("code_verifier", codeVerifier);
                });
        };
    }

    /**
     * Генерация code_verifier (случайная строка 43-128 символов)
     * RFC 7636: unreserved characters [A-Z] / [a-z] / [0-9] / "-" / "." / "_" / "~"
     */
    private String generateCodeVerifier() {
        SecureRandom secureRandom = new SecureRandom();
        byte[] codeVerifierBytes = new byte[32]; // 32 bytes = 43 chars after Base64URL
        secureRandom.nextBytes(codeVerifierBytes);
        return Base64.getUrlEncoder()
            .withoutPadding()
            .encodeToString(codeVerifierBytes);
    }

    /**
     * Генерация code_challenge = BASE64URL(SHA256(code_verifier))
     */
    private String generateCodeChallenge(String codeVerifier) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(codeVerifier.getBytes());
            return Base64.getUrlEncoder()
                .withoutPadding()
                .encodeToString(hash);
        } catch (Exception e) {
            throw new RuntimeException("Failed to generate code challenge", e);
        }
    }

}


