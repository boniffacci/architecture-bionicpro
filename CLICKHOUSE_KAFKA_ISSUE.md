# Проблема с ClickHouse Kafka Engine и Materialized Views

## Текущее состояние

### ✅ Что работает:
1. **Debezium CDC** - успешно захватывает изменения из PostgreSQL и отправляет в Kafka
2. **Kafka топики** - содержат данные (crm.public.users, telemetry.public.telemetry_events)
3. **ClickHouse подключение к Kafka** - consumer groups созданы, сообщения читаются
4. **Схема debezium** - создана в ClickHouse с таблицами users и telemetry_events
5. **Kafka Engine таблицы** - созданы и читают сообщения из Kafka

### ❌ Что не работает:
**Materialized Views не записывают данные в целевые таблицы**

## Диагностика

### Проверка чтения сообщений:
```sql
SELECT database, table, num_messages_read FROM system.kafka_consumers;
-- Результат: 70000+ сообщений прочитано из telemetry_events_kafka
--            7000+ сообщений прочитано из users_kafka
```

### Проверка данных в таблицах:
```sql
SELECT count() FROM debezium.users;
-- Результат: 0

SELECT count() FROM debezium.telemetry_events;
-- Результат: 0
```

### Структура Materialized View:
```sql
CREATE MATERIALIZED VIEW debezium.users_mv TO debezium.users AS
SELECT
    JSONExtractInt(JSONExtractString(payload, 'after'), 'id') AS user_id,
    JSONExtractString(JSONExtractString(payload, 'after'), 'user_uuid') AS user_uuid,
    ...
FROM debezium.users_kafka
WHERE JSONExtractString(payload, 'op') IN ('c', 'u', 'r')
```

## Возможные причины

### 1. Timing Issue
Materialized View была создана ПОСЛЕ того, как Kafka Engine таблица уже прочитала сообщения.
- Kafka Engine читает сообщения в фоне
- Когда MV создаётся, offset уже продвинут вперёд
- Новые сообщения должны триггерить MV, но этого не происходит

### 2. JSON Parsing Issue
Возможно, JSONExtract функции не могут корректно распарсить Debezium сообщения.
- Debezium использует сложную структуру с `schema` и `payload`
- Возможно, нужно использовать другой подход для парсинга

### 3. Materialized View TO Syntax
Синтаксис `CREATE MATERIALIZED VIEW ... TO table` может не работать корректно с Kafka Engine.
- Возможно, нужно использовать MV с собственным ENGINE
- Или использовать другой механизм для записи данных

## Попытки исправления

### ✅ Исправлено:
1. **Kafka broker address** - изменён с `kafka:9092` на `kafka:9093` (INTERNAL listener)
2. **Table engine** - изменён с Join на ReplacingMergeTree для users
3. **Consumer group offsets** - сброшены на earliest

### ❌ Не помогло:
1. Перезапуск ClickHouse
2. Пересоздание Materialized Views
3. Сброс consumer group offsets
4. Вставка новых записей в PostgreSQL

## Рекомендации

### Вариант 1: Использовать Materialized View с собственным ENGINE
Вместо:
```sql
CREATE MATERIALIZED VIEW debezium.users_mv TO debezium.users AS ...
```

Использовать:
```sql
CREATE MATERIALIZED VIEW debezium.users_mv
ENGINE = ReplacingMergeTree()
ORDER BY user_uuid
AS ...
```

### Вариант 2: Использовать ClickHouse Kafka Connect Sink
Вместо Kafka Engine + MV, использовать:
- Kafka Connect JDBC Sink Connector
- Прямая вставка данных из Kafka в ClickHouse через HTTP API

### Вариант 3: Использовать Python consumer
Создать отдельный Python сервис, который:
- Читает сообщения из Kafka
- Парсит Debezium JSON
- Вставляет данные в ClickHouse через clickhouse-connect

### Вариант 4: Упростить формат Debezium
Настроить Debezium на отправку упрощённого формата (без schema):
```json
{
  "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
  ...
  "key.converter.schemas.enable": "false",
  "value.converter.schemas.enable": "false"
}
```

## Следующие шаги

1. **Проверить логи ClickHouse** на наличие ошибок парсинга JSON
2. **Попробовать Вариант 1** - MV с собственным ENGINE
3. **Если не поможет** - реализовать Вариант 3 (Python consumer)
4. **Обновить тесты** - добавить проверку чтения сообщений из Kafka

## Полезные команды

### Проверка Kafka consumers:
```bash
docker compose exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list
docker compose exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --group clickhouse_crm_consumer --describe
```

### Проверка ClickHouse:
```sql
SELECT * FROM system.kafka_consumers;
SHOW CREATE TABLE debezium.users_kafka;
SHOW CREATE TABLE debezium.users_mv;
```

### Чтение сообщений из Kafka:
```bash
docker compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic crm.public.users --from-beginning --max-messages 1
```
