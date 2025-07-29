package hw;

import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.jwk.source.RemoteJWKSet;
import com.nimbusds.jose.proc.JWSVerificationKeySelector;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jose.jws.SignatureAlgorithm;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.oauth2.jwt.*;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.security.core.authority.mapping.SimpleAuthorityMapper;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.net.URL;
import java.util.Arrays;
import java.util.List;

@Configuration
@EnableWebSecurity
@EnableMethodSecurity(prePostEnabled = true) // включаем @PreAuthorize
public class SecurityConfig {

    private final String SECRET_KEY = "oNwoLQdvJAvRcL89SydqCWCe5ry1jMgq"; // 256-bit ключ

    @Bean
    public String jwtGrantedAuthoritiesPrefix() {
        return "SCOPE_";
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                .csrf(csrf -> csrf.disable())
                .cors(cors -> cors.configurationSource(corsConfigurationSource()))
                .authorizeHttpRequests(auth -> auth
                        .anyRequest().authenticated()
                )
                .oauth2ResourceServer(oauth2 -> oauth2
                        .jwt(jwt -> jwt
                                .decoder(jwtDecoder())
                                .jwtAuthenticationConverter(jwtAuthenticationConverter())
                        )
                );

        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(List.of("http://localhost:3000")); // Your frontend URL
        configuration.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(Arrays.asList("Authorization", "Cache-Control", "Content-Type"));
        configuration.setExposedHeaders(List.of("Authorization"));
        configuration.setAllowCredentials(true); // Important for cookies/session

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }

    @Bean
    public JwtDecoder jwtDecoder() {
        String jwkSetUri = "http://keycloak:8080/realms/reports-realm/protocol/openid-connect/certs";

        try {
            var url = new URL(jwkSetUri);
            return NimbusJwtDecoder.withJwkSetUri(jwkSetUri)
                    .jwsAlgorithm(SignatureAlgorithm.RS256)
                    .jwtProcessorCustomizer(processor -> {
                        // Configure the JWT processor to accept RS256
                        processor.setJWSKeySelector(new JWSVerificationKeySelector<>(
                                JWSAlgorithm.RS256,
                                new RemoteJWKSet<>(url)
                        ));
                    })
                    .build();
        } catch (Exception e) {
            throw new RuntimeException("Failed to configure JWT decoder", e);
        }
    }

    private JwtAuthenticationConverter jwtAuthenticationConverter() {
        JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
        //converter.setPrincipalClaimName("sub");
        converter.setJwtGrantedAuthoritiesConverter(jwt -> {
            if (jwt.hasClaim("realm_access")) {
                var roles = jwt.getClaimAsMap("realm_access").get("roles");
                if (roles instanceof List<?>) {
                    if (((List<?>) roles).contains("prothetic_user")) {
                        return java.util.List.of(new SimpleGrantedAuthority(jwtGrantedAuthoritiesPrefix() + "PROTHETIC_USER"));
                    }
                }
            }
            return java.util.List.of();
        });
        return converter;
    }
}
