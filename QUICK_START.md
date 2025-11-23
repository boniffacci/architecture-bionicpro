# Quick Start - Auth Proxy System

## Быстрый запуск

### 1. Установка зависимостей

```bash
# Python зависимости через uv
uv sync

# Playwright браузеры (сохраняются после перезагрузки)
./scripts/setup_playwright.sh

# Frontend зависимости
cd bionicpro_frontend
npm install
cd ..
```

### 2. Запуск всей системы

```bash
# Запускает: Keycloak, Redis, reports_api, auth_proxy, Frontend
./scripts/run_all_services.sh
```

Сервисы будут доступны на:
- **Frontend**: http://localhost:5173
- **auth_proxy**: http://localhost:3000
- **reports_api**: http://localhost:3002
- **Keycloak**: http://localhost:8080
- **Redis**: localhost:6379

### 3. Проверка работы

Откройте http://localhost:5173 в браузере:
1. Автоматический редирект на Keycloak
2. Введите: `user1` / `password123`
3. После входа увидите информацию о пользователе
4. Нажмите "Посмотреть reports_api/jwt" для проверки JWT

### 4. Запуск тестов

```bash
./scripts/run_tests.sh
```

Ожидаемый результат: **7 passed**

### 5. Остановка системы

```bash
./scripts/stop_all_services.sh
```

## Архитектура

```
┌─────────────┐
│  Frontend   │ (React, Vite)
│ :5173       │
└──────┬──────┘
       │ fetch (credentials: include)
       ↓
┌─────────────┐
│ auth_proxy  │ (FastAPI + PKCE)
│ :3000       │
└──┬────┬─────┘
   │    │
   │    └──────→ ┌──────────┐
   │             │ Keycloak │ (OIDC)
   │             │ :8080    │
   │             └──────────┘
   │
   ├──────────→ ┌──────────┐
   │            │  Redis   │ (Sessions)
   │            │ :6379    │
   │            └──────────┘
   │
   └──────────→ ┌──────────────┐
                │ reports_api  │ (FastAPI)
                │ :3002        │
                └──────────────┘
```

## Ключевые особенности

✅ **PKCE (SHA-256)** - защита Authorization Code Flow
✅ **Session Management** - сессии в Redis с rotation
✅ **HttpOnly Cookies** - защита от XSS
✅ **Single Session** - один пользователь = одна сессия
✅ **Auto Token Refresh** - автоматическое обновление через refresh token
✅ **No Refresh Token Exposure** - refresh token не выдается клиенту

## Тестовые пользователи

| Username    | Password      | Роль             |
|-------------|---------------|------------------|
| user1       | password123   | users            |
| admin1      | admin123      | administrators   |
| prosthetic1 | prosthetic123 | prosthetic_users |

## Полезные команды

```bash
# Запуск только auth_proxy
./scripts/start_auth_proxy.sh

# Запуск только reports_api
./scripts/start_reports_api.sh

# Остановка auth_proxy
./scripts/stop_auth_proxy.sh

# Остановка reports_api
./scripts/stop_reports_api.sh

# Просмотр логов
tail -f /tmp/auth_proxy.log
tail -f /tmp/reports_api.log
tail -f /tmp/frontend.log

# Очистка Redis
docker compose exec redis redis-cli FLUSHALL
```

## Troubleshooting

### Проблема: Тесты не проходят

```bash
# Убедитесь, что все сервисы запущены
./scripts/run_all_services.sh

# Очистите Redis
docker compose exec -T redis redis-cli FLUSHALL

# Запустите тесты снова
./scripts/run_tests.sh
```

### Проблема: Бесконечный редирект

Очистите cookies браузера и Redis:
```bash
docker compose exec -T redis redis-cli FLUSHALL
```

### Проблема: Playwright браузеры не найдены

```bash
./scripts/setup_playwright.sh
```

## Дополнительная информация

Полная документация: [AUTH_PROXY_README.md](./AUTH_PROXY_README.md)
