# Quick Start Guide - BionicPRO Reports Service

## 🚀 Быстрый запуск за 5 минут

### Шаг 1: Предварительные требования

```bash
# Проверьте Docker
docker --version
docker-compose --version

# Убедитесь, что Docker Desktop запущен
docker info
```

### Шаг 2: Запуск всех сервисов

```bash
# Перейдите в Task2
cd Task2

# Соберите все Docker образы
docker-compose build

# Запустите все сервисы
docker-compose up -d
```

### Шаг 3: Инициализация ClickHouse

```bash
# Подождите 30 секунд, пока сервисы запустятся, затем:

# Создайте таблицы в ClickHouse
docker exec bionicpro-clickhouse clickhouse-client --multiquery < olap/ddl/01_create_tables.sql

# Загрузите тестовые данные
docker exec bionicpro-clickhouse clickhouse-client --multiquery < olap/seed/sample_data.sql
```

### Шаг 4: Проверка работы

```bash
# Проверить статус сервисов
docker-compose ps

# Проверить здоровье API
curl -s http://localhost:8090/api/reports/health
```

Ожидаемый вывод:
```
Reports API is running
```

### Шаг 5: Получить JWT токен

```bash
# Получить токен от Keycloak
curl -s -X POST http://localhost:8080/realms/reports-realm/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=reports-frontend" \
  -d "username=prothetic1" \
  -d "password=prothetic123" | jq -r .access_token
```

Скопируйте полученный токен.

### Шаг 6: Тестирование API

```bash
# Установите токен в переменную окружения
export JWT_TOKEN="<ваш_токен>"

# Получите отчёт
curl -H "Authorization: Bearer $JWT_TOKEN" \
  "http://localhost:8090/api/reports/me?dateFrom=2024-01-01&dateTo=2024-01-31"
```

## 📊 Доступные сервисы

| Сервис | URL | Credentials |
|--------|-----|-------------|
| **Reports API** | http://localhost:8090/api | JWT токен |
| **Keycloak Admin** | http://localhost:8080 | admin / admin |
| **Airflow UI** | http://localhost:8091 | admin / admin |
| **ClickHouse HTTP** | http://localhost:8123 | default / (пусто) |

## 🔧 Полезные команды

### Управление сервисами

```bash
# Запустить все сервисы
docker-compose up -d

# Остановить все сервисы
docker-compose down

# Перезапустить все
docker-compose restart

# Показать все логи
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f reports-api
docker-compose logs -f etl-java
docker-compose logs -f airflow-scheduler

# Показать статус
docker-compose ps
```

### Работа с ClickHouse

```bash
# Создать таблицы
docker exec bionicpro-clickhouse clickhouse-client --multiquery < olap/ddl/01_create_tables.sql

# Загрузить тестовые данные
docker exec bionicpro-clickhouse clickhouse-client --multiquery < olap/seed/sample_data.sql

# Открыть ClickHouse shell
docker exec -it bionicpro-clickhouse clickhouse-client

# Выполнить SQL запрос
docker exec bionicpro-clickhouse clickhouse-client --query "SELECT * FROM mart_report_user_daily LIMIT 10"
```

### ETL команды

```bash
# Построить витрину
docker exec bionicpro-etl java -jar /app/etl-java.jar --job=buildMartJob

# Извлечь CRM
docker exec bionicpro-etl java -jar /app/etl-java.jar --job=extractCrmJob

# Извлечь телеметрию
docker exec bionicpro-etl java -jar /app/etl-java.jar --job=extractTelemetryJob

# Запустить весь ETL pipeline (последовательно)
docker exec bionicpro-etl java -jar /app/etl-java.jar --job=extractCrmJob && \
docker exec bionicpro-etl java -jar /app/etl-java.jar --job=extractTelemetryJob && \
docker exec bionicpro-etl java -jar /app/etl-java.jar --job=buildMartJob
```

### Разработка

```bash
# Собрать Reports API (Maven)
cd reports-api && mvn clean package -DskipTests

# Собрать ETL (Maven)
cd etl-java && mvn clean package -DskipTests

# Запустить API локально
cd reports-api && mvn spring-boot:run

# Запустить ETL локально
cd etl-java && mvn spring-boot:run
```

## 🧪 Тестовые сценарии

### Сценарий 1: Получить отчёт пользователя

```bash
# 1. Получить токен
TOKEN=$(curl -s -X POST http://localhost:8080/realms/reports-realm/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=reports-frontend" \
  -d "username=prothetic1" \
  -d "password=prothetic123" | jq -r .access_token)

# 2. Получить отчёт в JSON
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8090/api/reports/me?dateFrom=2024-01-01&dateTo=2024-01-31"

# 3. Получить отчёт в CSV
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8090/api/reports/me?dateFrom=2024-01-01&dateTo=2024-01-31&format=csv" \
  -o report.csv
```

### Сценарий 2: Запустить ETL вручную

```bash
# 1. Построить витрину для текущей даты
docker exec bionicpro-etl java -jar /app/etl-java.jar --job=buildMartJob

# 2. Проверить результат в ClickHouse
docker exec -it bionicpro-clickhouse clickhouse-client
# Затем в shell:
SELECT * FROM mart_report_user_daily WHERE report_date = today();
```

### Сценарий 3: Работа с Airflow

```bash
# 1. Открыть Airflow UI в браузере
open http://localhost:8091
# Или для Linux:
xdg-open http://localhost:8091

# 2. Войдите: admin / admin
# 3. В UI найдите DAG "bionicpro_reports_etl"
# 4. Включите DAG (toggle ON)
# 5. Запустите вручную (Trigger DAG)
```

## 🐛 Troubleshooting

### Проблема: Сервисы не запускаются

```bash
# Проверить логи
docker-compose logs -f

# Пересоздать всё с нуля
docker-compose down -v
docker-compose build
docker-compose up -d
docker exec bionicpro-clickhouse clickhouse-client --multiquery < olap/ddl/01_create_tables.sql
docker exec bionicpro-clickhouse clickhouse-client --multiquery < olap/seed/sample_data.sql
```

### Проблема: ClickHouse не инициализирован

```bash
# Вручную инициализировать
docker exec bionicpro-clickhouse clickhouse-client --multiquery < olap/ddl/01_create_tables.sql
docker exec bionicpro-clickhouse clickhouse-client --multiquery < olap/seed/sample_data.sql
```

### Проблема: API возвращает 401 Unauthorized

```bash
# Проверить токен
echo $JWT_TOKEN | cut -d'.' -f2 | base64 -d | jq

# Получить новый токен
TOKEN=$(curl -s -X POST http://localhost:8080/realms/reports-realm/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=reports-frontend" \
  -d "username=prothetic1" \
  -d "password=prothetic123" | jq -r .access_token)
```

### Проблема: ETL падает с ошибкой

```bash
# Проверить логи ETL
docker-compose logs -f etl-java

# Проверить подключение к ClickHouse
docker exec bionicpro-etl ping clickhouse
```

## 📝 Тестовые пользователи

| Username | Password | Role | user_id |
|----------|----------|------|---------|
| prothetic1 | prothetic123 | prothetic_user | user-001 |
| prothetic2 | prothetic123 | prothetic_user | user-002 |
| prothetic3 | prothetic123 | prothetic_user | user-003 |
| admin1 | admin123 | administrator | user-004 |

## 🔍 Проверка данных в ClickHouse

```bash
# Открыть ClickHouse shell
docker exec -it bionicpro-clickhouse clickhouse-client

# После входа в shell выполните:

# Посмотреть все таблицы
SHOW TABLES;

# Посмотреть витрину отчётов
SELECT * FROM mart_report_user_daily LIMIT 10;

# Посмотреть сырые данные CRM
SELECT * FROM raw_crm_users;

# Посмотреть сырую телеметрию
SELECT * FROM raw_telemetry;
```

Или выполнить запрос одной командой:

```bash
docker exec bionicpro-clickhouse clickhouse-client --query "SELECT * FROM mart_report_user_daily LIMIT 10"
```

## 📊 Примеры SQL запросов

### Отчёт по пользователю за период

```sql
SELECT
    user_id,
    report_date,
    metrics.name,
    metrics.value_avg
FROM mart_report_user_daily
WHERE user_id = 'user-001'
  AND report_date >= '2024-01-01'
  AND report_date <= '2024-01-31'
ORDER BY report_date DESC;
```

### Агрегация по регионам

```sql
SELECT
    region,
    count(*) as total_reports,
    avg(metrics.value_avg[1]) as avg_metric_value
FROM mart_report_user_daily
GROUP BY region;
```

### Топ пользователей по активности

```sql
SELECT
    user_id,
    sum(metrics.events_count[1]) as total_events
FROM mart_report_user_daily
GROUP BY user_id
ORDER BY total_events DESC
LIMIT 10;
```

## 🔄 Следующие шаги

1. **Изучите архитектуру**: [README.md](./README.md)
2. **Настройте Airflow**: Откройте http://localhost:8091
3. **Разработайте ETL jobs**: Смотрите `etl-java/src/main/java`
4. **Расширьте API**: Добавьте новые endpoints в `reports-api`
5. **Интегрируйте с Task1**: Используйте PKCE токены из Task1

## 📚 Дополнительные ресурсы

- [Полная документация](./README.md)
- [C4 Архитектурная диаграмма](./arch/bionicpro_reports_c4_container.puml)
- [ClickHouse DDL](./olap/ddl/01_create_tables.sql)
- [Airflow DAG](./airflow/dags/reports_etl_dag.py)

---

**Готово! Ваш Reports Service запущен и готов к использованию! 🎉**



