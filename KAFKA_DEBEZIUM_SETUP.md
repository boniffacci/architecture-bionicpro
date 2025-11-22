# Настройка Kafka + Debezium для CDC

## Обзор изменений

### 1. Рефакторинг CRM API
- **Customer** → **User** (модель ORM и таблица БД)
- **customers** → **users** (имя таблицы)
- Все тесты обновлены и проходят успешно

### 2. Рефакторинг Telemetry API
- **EmgSensorDataCreate** → **IncomingTelemetryEvent** (входящие данные)
- **EmgSensorData** → **TelemetryEvent** (модель БД)
- **emg_sensor_data** → **telemetry_events** (имя таблицы)
- **signal_time** → **created_ts** (переименование поля)
- Добавлено поле **event_uuid** (уникальное, индексированное)
- TelemetryEvent наследуется от IncomingTelemetryEvent
- Автоматическая генерация event_uuid, если не задан
- Все тесты обновлены и проходят успешно

### 3. Docker Compose
Добавлены новые сервисы:
- **Zookeeper** - координация Kafka (порт 2181)
- **Kafka** - брокер сообщений (порт 29092)
- **Kafdrop** - веб-интерфейс для Kafka (порт 9100)
- **Debezium** - Kafka Connect для CDC (порт 8083)

PostgreSQL БД (crm_db и telemetry_db) настроены с `wal_level=logical` для поддержки репликации.

### 4. ClickHouse
Добавлена схема **debezium** с таблицами:
- **users_kafka** (Kafka Engine) - читает из топика `crm.public.users`
- **users_join** (Join Engine) - хранит пользователей для JOIN-запросов
- **users_mv** (Materialized View) - парсит JSON и записывает в users_join
- **telemetry_events_kafka** (Kafka Engine) - читает из топика `telemetry.public.telemetry_events`
- **telemetry_events_merge** (MergeTree) - хранит события телеметрии
- **telemetry_events_mv** (Materialized View) - парсит JSON и записывает в telemetry_events_merge

## Быстрый старт

### 1. Остановка и очистка старой инфраструктуры
```bash
# Останавливаем все контейнеры и удаляем volumes
docker compose down -v

# Удаляем данные PostgreSQL (опционально, для чистого старта)
sudo rm -rf postgres-crm-data postgres-telemetry-data clickhouse-data
```

### 2. Запуск инфраструктуры
```bash
# Запускаем все сервисы
docker compose up -d

# Проверяем статус
docker compose ps
```

### 3. Ожидание готовности сервисов
```bash
# Ждём, пока все сервисы запустятся (примерно 30-60 секунд)
# Проверяем Debezium
curl http://localhost:8083/

# Проверяем Kafdrop
curl http://localhost:9100/

# Проверяем ClickHouse
curl -u default:clickhouse_password http://localhost:8123/
```

### 4. Настройка Debezium-коннекторов
```bash
# Создаём коннекторы для crm_db и telemetry_db
./scripts/setup_debezium_connectors.sh
```

### 5. Настройка ClickHouse Kafka Engine
```bash
# Создаём таблицы в ClickHouse для чтения из Kafka
./scripts/setup_clickhouse_kafka.sh
```

### 6. Запуск микросервисов
```bash
# В отдельных терминалах запускаем:

# CRM API (порт 3002)
uv run python -m crm_api.main

# Telemetry API (порт 3003)
uv run python -m telemetry_api.main
```

### 7. Тестирование интеграции
```bash
# Запускаем полный тест
./scripts/test_kafka_debezium.sh
```

## Проверка работоспособности

### 1. Веб-интерфейсы
- **Kafdrop** (Kafka UI): http://localhost:9100
- **Debezium REST API**: http://localhost:8083/connectors

### 2. Проверка Kafka-топиков
```bash
# Через Kafdrop (веб-интерфейс)
# Открыть http://localhost:9100

# Или через curl
curl http://localhost:8083/connectors/crm-connector/status
curl http://localhost:8083/connectors/telemetry-connector/status
```

### 3. Наполнение БД тестовыми данными
```bash
# CRM DB (1000 пользователей)
curl -X POST http://localhost:3002/populate_base

# Telemetry DB (10000 событий)
curl -X POST http://localhost:3003/populate_base
```

### 4. Проверка данных в ClickHouse
```bash
# Подключение к ClickHouse
clickhouse-client --host localhost --port 9431 --user default --password clickhouse_password

# Или через HTTP
curl -u default:clickhouse_password "http://localhost:8123/" -d "SELECT count() FROM debezium.users_join"
curl -u default:clickhouse_password "http://localhost:8123/" -d "SELECT count() FROM debezium.telemetry_events_merge"

# Просмотр данных
curl -u default:clickhouse_password "http://localhost:8123/" -d "SELECT * FROM debezium.users_join LIMIT 5 FORMAT Pretty"
curl -u default:clickhouse_password "http://localhost:8123/" -d "SELECT * FROM debezium.telemetry_events_merge LIMIT 5 FORMAT Pretty"
```

## Архитектура потока данных

```
┌─────────────┐      ┌──────────────┐      ┌─────────┐      ┌─────────────┐
│  CRM API    │─────▶│   crm_db     │─────▶│Debezium │─────▶│    Kafka    │
│  (port 3002)│      │ (PostgreSQL) │      │         │      │             │
└─────────────┘      └──────────────┘      └─────────┘      └──────┬──────┘
                                                                    │
┌─────────────┐      ┌──────────────┐                              │
│Telemetry API│─────▶│telemetry_db  │─────▶Debezium ──────────────┤
│  (port 3003)│      │ (PostgreSQL) │                              │
└─────────────┘      └──────────────┘                              │
                                                                    ▼
                                                            ┌───────────────┐
                                                            │  ClickHouse   │
                                                            │  (OLAP DB)    │
                                                            │               │
                                                            │ Schema:       │
                                                            │ - debezium    │
                                                            └───────────────┘
```

## Kafka-топики

### crm.public.users
- Источник: таблица `users` в `crm_db`
- Формат: Debezium JSON (с полями `before`, `after`, `op`)
- Потребитель: ClickHouse Kafka Engine (`debezium.users_kafka`)

### telemetry.public.telemetry_events
- Источник: таблица `telemetry_events` в `telemetry_db`
- Формат: Debezium JSON (с полями `before`, `after`, `op`)
- Потребитель: ClickHouse Kafka Engine (`debezium.telemetry_events_kafka`)

## Запуск тестов

```bash
# Тесты CRM API
uv run pytest crm_api/test_crm_api.py -v

# Тесты Telemetry API
uv run pytest telemetry_api/test_telemetry_api.py -v

# Все тесты
uv run pytest -v
```

## Troubleshooting

### Debezium не создаёт топики
1. Проверьте статус коннекторов: `curl http://localhost:8083/connectors/crm-connector/status`
2. Проверьте логи Debezium: `docker logs debezium`
3. Убедитесь, что PostgreSQL настроен с `wal_level=logical`

### ClickHouse не получает данные из Kafka
1. Проверьте, что Kafka-топики существуют (через Kafdrop)
2. Проверьте логи ClickHouse: `docker logs olap_db`
3. Проверьте, что Materialized View созданы: `SHOW TABLES FROM debezium`

### Данные не появляются в ClickHouse
1. Убедитесь, что данные есть в PostgreSQL
2. Проверьте, что Debezium-коннекторы работают
3. Проверьте, что в Kafka-топиках есть сообщения (через Kafdrop)
4. Подождите 10-15 секунд для репликации

## Полезные команды

```bash
# Перезапуск Debezium
docker restart debezium

# Удаление и пересоздание коннекторов
curl -X DELETE http://localhost:8083/connectors/crm-connector
curl -X DELETE http://localhost:8083/connectors/telemetry-connector
./scripts/setup_debezium_connectors.sh

# Очистка Kafka-топиков (через удаление и пересоздание)
docker compose restart kafka

# Очистка ClickHouse
clickhouse-client --host localhost --port 9431 --user default --password clickhouse_password \
  -q "DROP DATABASE IF EXISTS debezium"
./scripts/setup_clickhouse_kafka.sh
```
