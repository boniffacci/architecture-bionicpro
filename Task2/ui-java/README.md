# BionicPRO UI (Java) - Spring MVC + Thymeleaf

> Java-based UI приложение с OAuth2 PKCE интеграцией

## 📋 Обзор

Полностью Java-based UI приложение, построенное на:
- **Spring Boot 3.2.0** - Framework
- **Spring MVC** - Web layer
- **Thymeleaf** - Template engine
- **Spring Security OAuth2 Client** - PKCE authentication
- **Tailwind CSS** - Styling

## 🔐 Безопасность

### PKCE Flow

Приложение использует **PKCE (Proof Key for Code Exchange)** для защиты OAuth2 Authorization Code Flow:

```
1. User clicks "Login"
2. App generates code_verifier (random string)
3. App calculates code_challenge = SHA256(code_verifier)
4. Redirect to Keycloak with code_challenge
5. User authenticates in Keycloak
6. Keycloak redirects back with authorization code
7. App exchanges code + code_verifier for tokens
8. Keycloak verifies: SHA256(code_verifier) == code_challenge
9. If valid → tokens issued, user logged in
```

### BFF Pattern

Приложение работает как **Backend for Frontend (BFF)**:
- Токены хранятся на сервере (в сессии)
- Токены не передаются в браузер
- Вызовы к Reports API выполняются с сервера
- CSRF защита включена

## 🏗️ Архитектура

```
┌──────────┐    PKCE     ┌──────────┐
│  Browser │◄───────────►│  UI Java │
└──────────┘             │ (Thymeleaf)│
                         └─────┬──────┘
                               │
                    ┌──────────┼──────────┐
                    │                     │
            ┌───────▼────────┐    ┌──────▼────────┐
            │   Keycloak     │    │ Reports API   │
            │ (OAuth2 + PKCE)│    │(Spring Boot)  │
            └────────────────┘    └───────────────┘
```

## 📂 Структура проекта

```
ui-java/
├── src/main/java/com/bionicpro/ui/
│   ├── UiApplication.java              # Main class
│   ├── config/
│   │   └── SecurityConfig.java         # OAuth2 + PKCE config
│   ├── controller/
│   │   ├── HomeController.java         # Home/login pages
│   │   └── ReportsController.java      # Reports pages
│   └── service/
│       └── ReportsApiService.java      # Reports API client
├── src/main/resources/
│   ├── application.yaml                # Configuration
│   └── templates/                      # Thymeleaf templates
│       ├── index.html                  # Landing page
│       ├── login.html                  # Login page
│       ├── reports.html                # Reports page
│       └── layout.html                 # Base layout
├── pom.xml
├── Dockerfile
└── README.md
```

## 🚀 Быстрый старт

### Локальный запуск

```bash
# 1. Убедитесь, что Keycloak запущен
docker-compose up -d keycloak

# 2. Запустите приложение
cd ui-java
mvn spring-boot:run
```

### Docker запуск

```bash
# Из корневой директории Task2
docker-compose up -d ui-java
```

## 🌐 Endpoints

| Endpoint | Описание |
|----------|----------|
| `GET /` | Главная страница (landing) |
| `GET /login` | Страница логина |
| `GET /reports` | Страница отчётов (требуется auth) |
| `GET /reports/data` | Получить данные отчёта (AJAX) |
| `GET /reports/download` | Скачать отчёт в CSV |
| `POST /logout` | Выход из системы |

## ⚙️ Конфигурация

### application.yaml

Ключевые настройки:

```yaml
server:
  port: 8085

spring:
  security:
    oauth2:
      client:
        registration:
          keycloak:
            client-id: bionicpro-ui
            scope: openid, profile, email
            authorization-grant-type: authorization_code
        provider:
          keycloak:
            issuer-uri: http://localhost:8080/realms/reports-realm

bionicpro:
  api:
    base-url: http://localhost:8090/api
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KEYCLOAK_CLIENT_ID` | bionicpro-ui | OAuth2 client ID |
| `KEYCLOAK_ISSUER_URI` | http://localhost:8080/realms/reports-realm | Keycloak issuer |
| `REPORTS_API_URL` | http://localhost:8090/api | Reports API URL |

## 🧪 Тестирование

### 1. Открыть приложение

```bash
open http://localhost:8085
```

### 2. Нажать "Войти"

Вы будете перенаправлены в Keycloak для аутентификации.

### 3. Войти с тестовым пользователем

- Username: `prothetic1`
- Password: `prothetic123`

### 4. Проверить PKCE в DevTools

**Network → Authorization request:**
```
code_challenge=<BASE64_STRING>
code_challenge_method=S256
```

**Token request:**
```
code_verifier=<ORIGINAL_STRING>
```

## 🔍 Особенности реализации

### 1. Автоматическая генерация PKCE параметров

`SecurityConfig.java` автоматически генерирует:
```java
code_verifier = random(32 bytes)
code_challenge = BASE64URL(SHA256(code_verifier))
```

### 2. Server-side токены

Токены хранятся в Spring Session (по умолчанию в памяти):
```java
@RegisteredOAuth2AuthorizedClient("keycloak") 
OAuth2AuthorizedClient authorizedClient
```

### 3. Вызовы к Reports API

```java
WebClient webClient = webClientBuilder
    .baseUrl(apiBaseUrl)
    .defaultHeader("Authorization", "Bearer " + accessToken)
    .build();
```

### 4. Thymeleaf Security Integration

```html
<div sec:authorize="isAuthenticated()">
    <span sec:authentication="name">User</span>
</div>
```

## 📊 Сравнение с React Frontend

| Аспект | React (Task1) | Java UI (Task2) |
|--------|---------------|-----------------|
| **Framework** | React + TypeScript | Spring MVC + Thymeleaf |
| **PKCE** | keycloak-js (client-side) | Spring Security (server-side) |
| **Токены** | Browser storage | Server session |
| **Rendering** | Client-side (SPA) | Server-side (SSR) |
| **Безопасность** | Токены в браузере | Токены на сервере (BFF) |
| **SEO** | Требует SSR | Изначально SSR |

**Преимущества Java UI:**
- ✅ Полностью серверная обработка токенов (BFF pattern)
- ✅ Нет утечки токенов в браузер
- ✅ Лучший контроль над сессиями
- ✅ Встроенная CSRF защита
- ✅ SEO-friendly из коробки

## 🔧 Разработка

### Hot Reload

Spring DevTools включен для автоматической перезагрузки:

```bash
mvn spring-boot:run
```

Изменения в templates и Java классах применяются автоматически.

### Debug Logging

В `application.yaml`:

```yaml
logging:
  level:
    com.bionicpro: DEBUG
    org.springframework.security.oauth2: DEBUG
```

## 🐛 Troubleshooting

### Проблема: OAuth2 redirect не работает

**Решение:**
Проверьте Keycloak redirect URIs для клиента `bionicpro-ui`:
```
http://localhost:8085/*
http://localhost:8085/login/oauth2/code/keycloak
```

### Проблема: Ошибка PKCE validation

**Решение:**
Убедитесь, что в Keycloak включен PKCE:
```json
{
  "attributes": {
    "pkce.code.challenge.method": "S256"
  }
}
```

### Проблема: Reports API недоступен

**Решение:**
Проверьте URL Reports API в конфигурации:
```bash
curl http://localhost:8090/api/reports/health
```

## 📚 Документация

- [Spring Security OAuth2 Client](https://docs.spring.io/spring-security/reference/servlet/oauth2/client/index.html)
- [Thymeleaf Documentation](https://www.thymeleaf.org/documentation.html)
- [RFC 7636 - PKCE](https://datatracker.ietf.org/doc/html/rfc7636)

## 🎯 Следующие шаги

1. **Кэширование**: Добавить Redis для распределённых сессий
2. **Rate Limiting**: Защита от перегрузки API
3. **i18n**: Поддержка нескольких языков
4. **Темная тема**: CSS переключатель темы
5. **Графики**: Добавить Chart.js для визуализации

---

**Java UI готов к использованию с полной PKCE защитой!** 🎉


