# Auth Proxy - Сервис авторизации с OIDC и управлением сессиями

## Обзор

Разработан новый прокси-сервис `auth_proxy`, который инкапсулирует всё общение с Keycloak и управляет сессиями пользователей через Redis.

## Архитектура

```
Фронтэнд (React) → auth_proxy (FastAPI) → Keycloak (OIDC)
                         ↓
                      Redis (сессии)
                         ↓
                   reports_backend (FastAPI)
```

## Основные компоненты

### 1. auth_proxy (`/auth_proxy/`)

**Файлы:**
- `app.py` - основное FastAPI приложение с эндпоинтами
- `config.py` - конфигурация сервиса
- `models.py` - модели данных (UserInfo, SessionData, ProxyRequest)
- `session_manager.py` - менеджер сессий с Redis
- `keycloak_client.py` - клиент для работы с Keycloak OIDC
- `main.py` - точка входа для запуска сервиса

**Эндпоинты:**
- `GET /user_info` - информация о текущем пользователе
- `GET /sign_in` - начало процесса авторизации через Keycloak
- `POST /sign_out` - выход из системы
- `GET /callback` - callback для завершения OIDC flow
- `POST /proxy` - проксирование запросов к upstream-сервисам с JWT
- `GET /health` - health check

**Особенности:**
- ✅ Инкапсуляция всего общения с Keycloak
- ✅ **PKCE (Proof Key for Code Exchange)** с SHA-256
- ✅ Refresh token не выдается наружу
- ✅ Сессии хранятся в Redis
- ✅ Session cookie с настройками: HttpOnly, SameSite=lax
- ✅ Session rotation при каждом запросе к /proxy
- ✅ Single session per user (опционально для определенных ролей)
- ✅ Автоматическое обновление access token через refresh token

### 2. reports_backend

**Новый эндпоинт:**
- `GET /jwt` - возвращает содержимое JWT токена (для отладки)

### 3. Фронтэнд (bionicpro-frontend)

**Новые файлы:**
- `src/App_new.tsx` - React-приложение без Keycloak SDK
- `src/main_new.tsx` - точка входа без Keycloak Provider

**Особенности:**
- Работает только через auth_proxy
- Проверяет авторизацию через `/user_info`
- Автоматический редирект на `/sign_in` при отсутствии авторизации
- Кнопка "Посмотреть reports_api/jwt" для проверки JWT

### 4. Docker Compose

**Добавлен сервис:**
- `redis` - Redis 7 Alpine для хранения сессий

### 5. Bash-скрипты (`/scripts/`)

**Управление сервисами:**
- `start_reports_api.sh` - запуск reports_api через uv
- `start_auth_proxy.sh` - запуск auth_proxy через uv
- `stop_reports_api.sh` - остановка reports_api
- `stop_auth_proxy.sh` - остановка auth_proxy
- `run_all_services.sh` - запуск всех сервисов (Docker + Python + Frontend)
- `stop_all_services.sh` - остановка всех сервисов

**Тестирование:**
- `setup_playwright.sh` - установка Playwright браузеров
- `run_tests.sh` - запуск E2E тестов

### 6. Тесты (`/tests/`)

**Новый файл:**
- `test_e2e_auth_proxy.py` - E2E тесты для новой архитектуры с auth_proxy

**Тестовые классы:**
- `TestServiceAvailability` - проверка доступности сервисов
- `TestAuthProxyAuthentication` - тесты авторизации через auth_proxy
- `TestFullE2EFlow` - полный E2E тест

## Конфигурация

### Keycloak

Добавлен новый client `auth-proxy` в `keycloak/realm-export.json`:
- Client ID: `auth-proxy`
- Client Secret: `auth-proxy-secret-key-12345`
- Type: Confidential
- Standard Flow: Enabled
- Redirect URIs: `http://localhost:3002/callback`, `http://localhost:3002/*`

### auth_proxy настройки (config.py)

```python
# Redis
redis_host = "localhost"
redis_port = 6379

# Keycloak
keycloak_url = "http://localhost:8080"
keycloak_realm = "reports-realm"
client_id = "auth-proxy"
client_secret = "auth-proxy-secret-key-12345"

# Session
session_lifetime_seconds = 3600  # 1 час
session_cookie_httponly = True
session_cookie_samesite = "lax"
enable_session_rotation = True
single_session_per_user = True
```

## Запуск системы

### 1. Установка зависимостей

```bash
# Python зависимости
uv sync

# Playwright браузеры
./scripts/setup_playwright.sh

# Frontend зависимости
cd bionicpro-frontend
npm install
```

### 2. Запуск всех сервисов

```bash
./scripts/run_all_services.sh
```

Это запустит:
- Keycloak (http://localhost:8080)
- Redis (localhost:6379)
- reports_api (http://localhost:3001)
- auth_proxy (http://localhost:3002)
- Frontend (http://localhost:5173)

### 3. Запуск тестов

```bash
./scripts/run_tests.sh
```

### 4. Остановка всех сервисов

```bash
./scripts/stop_all_services.sh
```

## Использование

### Авторизация пользователя

1. Откройте http://localhost:5173
2. Фронтэнд автоматически перенаправит на auth_proxy `/sign_in`
3. auth_proxy перенаправит на Keycloak
4. После ввода учетных данных (user1/password123) произойдет редирект обратно
5. auth_proxy создаст сессию в Redis и установит session cookie
6. Фронтэнд отобразит информацию о пользователе

### Проксирование запросов

Фронтэнд обращается к reports_api через auth_proxy:

```typescript
const response = await fetch(`${AUTH_PROXY_URL}/proxy`, {
  method: 'POST',
  credentials: 'include',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    upstream_uri: 'http://localhost:3001/jwt',
    redirect_to_sign_in: false,
  }),
})
```

auth_proxy:
1. Проверяет session cookie
2. Обновляет access token при необходимости
3. Добавляет JWT в заголовок Authorization
4. Проксирует запрос к upstream
5. Выполняет session rotation (новый session_id)
6. Возвращает ответ (без JWT в заголовках)

## Безопасность

### Реализованные меры

✅ **Refresh token не выдается наружу** - хранится только в Redis
✅ **HttpOnly cookies** - защита от XSS
✅ **SameSite=lax** - защита от CSRF
✅ **Session rotation** - новый session_id при каждом запросе
✅ **Single session per user** - только одна активная сессия
✅ **Автоматическое обновление токенов** - через refresh token
✅ **CORS настроен** - только для разрешенных origins

### Будущие улучшения

- [ ] HTTPS для production
- [ ] Rate limiting
- [ ] Логирование всех действий с сессиями
- [ ] Мониторинг активных сессий
- [ ] Настройка single session только для определенных ролей (administrators)

## Тестирование

### Результаты E2E тестов

✅ **Все тесты проходят успешно** (7/7 passed)

```bash
tests/test_e2e_auth_proxy.py::TestServiceAvailability::test_frontend_responds PASSED
tests/test_e2e_auth_proxy.py::TestServiceAvailability::test_backend_responds PASSED
tests/test_e2e_auth_proxy.py::TestServiceAvailability::test_auth_proxy_responds PASSED
tests/test_e2e_auth_proxy.py::TestAuthProxyAuthentication::test_user_info_unauthorized PASSED
tests/test_e2e_auth_proxy.py::TestAuthProxyAuthentication::test_login_flow PASSED
tests/test_e2e_auth_proxy.py::TestAuthProxyAuthentication::test_jwt_endpoint_via_proxy PASSED
tests/test_e2e_auth_proxy.py::TestFullE2EFlow::test_complete_flow PASSED
```

### Проверка PKCE

В логах и URL видно использование PKCE:
```
code_challenge=-7jRltw3RoGTvj7L5wmI9WRMgxBBr2fOt7NbiL0iESg
code_challenge_method=S256
```

## Известные ограничения

1. **Session rotation в /proxy** - может вызывать проблемы при параллельных запросах. Рекомендуется отключить для некоторых эндпоинтов.

2. **CORS настройки** - в production нужно указывать конкретные origins вместо списка.

## Зависимости

### Python (pyproject.toml)

```toml
dependencies = [
    "fastapi>=0.121.0",
    "httpx>=0.27.0",
    "pyjwt[crypto]>=2.9.0",
    "uvicorn>=0.38.0",
    "redis>=5.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "authlib>=1.3.0",
    "pytest>=8.0.0",
    "pytest-playwright>=0.4.0",
    "playwright>=1.40.0",
]
```

## Логи

Логи сервисов сохраняются в `/tmp/`:
- `/tmp/reports_api.log`
- `/tmp/auth_proxy.log`
- `/tmp/frontend.log`

## Порты

- **8080** - Keycloak
- **6379** - Redis
- **3001** - reports_api
- **3002** - auth_proxy
- **5173** - Frontend (Vite dev server)

## Тестовые пользователи

- **user1** / password123 (роль: users)
- **admin1** / admin123 (роль: administrators)
- **prothetic1** / prothetic123 (роль: prothetic_users)
