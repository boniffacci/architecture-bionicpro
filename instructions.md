# BionicPRO Security Enhancement - Инструкции по запуску

## TL;DR

1. Поднять окружение

```bash
docker-compose up -d --build
```

2. Зайти на `https://localhost:3000`

3. Взять креды `paige.gonzales`:`bionicpro123`

4. MFA по FreeOTP (предложит отсканировать QR)

5. См. отчёт

6. Посмотреть Airflow: `http://localhost:8083`. Креды `admin`:`admin`


## Обзор системы

Система BionicPRO была переработана для повышения безопасности и включает в себя:

1. **OAuth 2.0 с PKCE** - защищенная аутентификация
2. **LDAP интеграция** - для международных представительств
3. **MFA (TOTP)** - двухфакторная аутентификация
4. **Яндекс ID** - внешний провайдер аутентификации
5. **Сервис отчетов** - с кешированием в S3 и CDN
6. **CDC с Debezium** - для реального времени данных
7. **Предзагруженные отчеты** - тестовые данные для трех CRM пользователей

## Требования

- Docker и Docker Compose
- Go 1.21+ (для локальной разработки)
- Node.js 18+ (для frontend)

## Запуск системы

### 1. Клонирование и подготовка

```bash
git clone <repository-url>
cd architecture-bionicpro
```

### 2. Запуск всех сервисов

```bash
docker-compose up -d --build
```

### 3. Ожидание запуска сервисов

Подождите 2-3 минуты для полного запуска всех сервисов, особенно Keycloak и Airflow.

### 4. Проверка статуса

```bash
docker-compose ps
```

Все сервисы должны быть в состоянии "Up".

## Доступные сервисы

| Сервис | URL | Описание |
|--------|-----|----------|
| Frontend | http://localhost:3000 | React приложение |
| BionicPRO Auth | http://localhost:5001 | Go сервис аутентификации |
| Reports API | http://localhost:5003 | Go сервис отчетов |
| Keycloak | http://localhost:8080 | Identity Provider |
| Airflow UI | http://localhost:8083 | ETL процессы |
| ClickHouse | http://localhost:8123 | OLAP база данных |
| MinIO | http://localhost:9001 | S3 совместимое хранилище |
| Nginx CDN | http://localhost:8888 | CDN для отчетов |
| Kafka UI | http://localhost:8082 | Kafka управление |
| Debezium | http://localhost:8084 | CDC коннектор |

## Тестовые учетные данные

### CRM пользователи (MFA обязательно, с предзагруженными отчетами)
- **alexis.moore** / **bionicpro123** (CRM ID: 1, 15 записей отчетов)
- **paige.gonzales** / **bionicpro123** (CRM ID: 2, 5 записей отчетов)
- **theresa.kelly** / **bionicpro123** (CRM ID: 3, 15 записей отчетов)

### LDAP пользователи (MFA обязательно)
- **john.doe** / **password**
- **jane.smith** / **password**
- **alex.johnson** / **password**

### Тестовые пользователи (MFA обязательно)
- **testuser** / **password123**
- **buyer** / **buyer123**

### Яндекс ID
- Войдите через Яндекс ID на странице входа в Keycloak
- MFA не требуется для Яндекс ID

## Настройка MFA

1. Войдите в систему с любыми учетными данными
2. Keycloak автоматически запросит настройку MFA
3. Отсканируйте QR-код в Google Authenticator или FreeOTP
4. Введите 6-значный код для завершения настройки

### Просмотр логов

```bash
# Логи всех сервисов
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f bionicpro-auth
docker-compose logs -f reports-api
docker-compose logs -f keycloak
```

### Проверка здоровья сервисов

```bash
# Проверка здоровья
curl http://localhost:5001/health
curl http://localhost:5003/health
curl http://localhost:8080/realms/reports-realm/.well-known/openid-configuration
```

## Устранение неполадок

### Проблемы с запуском

1. **Порты заняты**: Проверьте, что порты 3000, 5001, 5003, 8080 свободны
2. **Недостаточно памяти**: Увеличьте лимиты Docker
3. **Медленный запуск**: Подождите 3-5 минут для полной инициализации

### Проблемы с аутентификацией

1. **Ошибка "Bearer-only not allowed"**: Перезапустите Keycloak
2. **MFA не работает**: Проверьте настройки в Keycloak Admin Console
3. **LDAP не работает**: Проверьте подключение к OpenLDAP

### Проблемы с отчетами

1. **Нет данных**: При первом запуске система автоматически загружает тестовые данные отчетов для трех CRM пользователей (alexis.moore, paige.gonzales, theresa.kelly)
2. **Ошибки ClickHouse**: Проверьте подключение к базе данных
3. **Проблемы с S3**: Проверьте настройки MinIO

### Тестирование предзагруженных отчетов

При первом запуске системы автоматически создаются тестовые данные отчетов:

```bash
# Проверка отчета для alexis.moore (CRM ID: 1)
curl -s http://localhost:5003/api/v1/reports -H "X-User-ID: 1" | jq .

# Проверка отчета для paige.gonzales (CRM ID: 2)
curl -s http://localhost:5003/api/v1/reports -H "X-User-ID: 2" | jq .

# Проверка отчета для theresa.kelly (CRM ID: 3)
curl -s http://localhost:5003/api/v1/reports -H "X-User-ID: 3" | jq .
```

Пример ответа:
```json
{
  "user_id": 2,
  "username": "",
  "email": "",
  "total_sessions": 7,
  "total_usage_time": 23800,
  "average_session_time": 3400,
  "last_activity": "2024-01-19T00:00:00Z",
  "report_generated_at": "2025-10-19T18:41:04.791552671Z",
  "has_data": true
}
```

## Разработка

### Локальная разработка Go сервисов

```bash
# BionicPRO Auth
cd backend/bionicpro-auth
go mod download
go run main.go

# Reports Service  
cd backend/reports-service
go mod download
go run main.go
```

### Пересборка сервисов

```bash
# Пересборка конкретного сервиса
docker-compose build bionicpro-auth
docker-compose up -d bionicpro-auth

# Пересборка всех сервисов
docker-compose build
docker-compose up -d
```

## Остановка системы

```bash
# Остановка всех сервисов
docker-compose down

# Остановка с удалением volumes (ВНИМАНИЕ: удалит все данные)
docker-compose down -v
```
