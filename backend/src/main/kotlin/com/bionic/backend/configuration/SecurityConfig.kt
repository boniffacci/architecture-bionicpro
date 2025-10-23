package com.bionic.backend.configuration


import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.core.convert.converter.Converter
import org.springframework.security.authentication.AbstractAuthenticationToken
import org.springframework.security.config.web.server.ServerHttpSecurity
import org.springframework.security.oauth2.jwt.Jwt
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken
import org.springframework.security.web.server.SecurityWebFilterChain
import reactor.core.publisher.Mono

@Configuration
class SecurityConfig {

    @Bean
    fun securityWebFilterChain(http: ServerHttpSecurity): SecurityWebFilterChain =
        http
            .cors { it.disable() }
            .csrf { it.disable() }
            .formLogin { it.disable() }
            .authorizeExchange {
                it.anyExchange().authenticated()
            }
            .oauth2ResourceServer { oauth2 ->
                oauth2.jwt { jwt ->
                    jwt.jwtAuthenticationConverter(jwtAuthConverter())
                }
            }
            .build()

    private fun jwtAuthConverter(): Converter<Jwt, Mono<out AbstractAuthenticationToken>> =
        Converter { jwt ->
            val principal = jwt.getClaimAsString("preferred_username") ?: jwt.subject
            Mono.just(JwtAuthenticationToken(jwt, listOf(), principal))
        }
}