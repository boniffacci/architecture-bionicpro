#!/bin/bash

# Скрипт для инициализации Debezium-коннекторов при старте контейнера
# Запускается автоматически после старта Kafka Connect

set -e

echo "========================================="
echo "Инициализация Debezium-коннекторов"
echo "========================================="

# Ожидаем запуска Debezium Kafka Connect
echo "Ожидание запуска Debezium Kafka Connect..."
for i in {1..60}; do
  if curl -s -f http://localhost:8083/ > /dev/null 2>&1; then
    echo "✓ Debezium Kafka Connect начал отвечать (попытка $i)"
    sleep 5
    echo "✓ Debezium Kafka Connect готов к работе"
    break
  fi
  echo "Ожидание Debezium... (попытка $i/60)"
  sleep 2
done

# Проверяем, что Debezium доступен
if ! curl -s -f http://localhost:8083/ > /dev/null 2>&1; then
  echo "✗ Debezium Kafka Connect не запустился"
  exit 1
fi

# Дополнительная пауза для инициализации PostgreSQL баз данных
# Docker Compose уже ждёт healthcheck, но добавляем небольшую паузу для надёжности
echo ""
echo "Дополнительная пауза для инициализации PostgreSQL баз данных..."
sleep 5

echo ""
echo "========================================="
echo "Создание коннектора для CRM DB"
echo "========================================="

# Создаём коннектор для crm_db (таблица users)
curl -i -X POST -H "Accept:application/json" -H "Content-Type:application/json" \
  http://localhost:8083/connectors/ -d '{
  "name": "crm-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "tasks.max": "1",
    "database.hostname": "crm-db",
    "database.port": "5432",
    "database.user": "debezium_user",
    "database.password": "debezium_password",
    "database.dbname": "crm_db",
    "database.server.name": "crm",

    "topic.prefix": "crm",
    "plugin.name": "pgoutput",
    "slot.name": "debezium_crm",
    "publication.name": "crm_debezium_publication",
    "slot.drop.on.stop": "false",
    "snapshot.mode": "initial",
    "snapshot.fetch.size": "1000",

    "schema.include.list": "public",
    "table.include.list": "public.users",

    "key.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",

    "key.converter.schemas.enable": "true",
    "value.converter.schemas.enable": "true",

    "provide.transaction.metadata": "false",
    "time.precision.mode": "adaptive_time_microseconds",

    "decimal.handling.mode": "double",
    "heartbeat.interval.ms": "10000",

    "max.batch.size": "2048",
    "poll.interval.ms": "1000",

    "include.schema.changes": "false"
  }
}'

echo ""
echo ""
echo "========================================="
echo "Создание коннектора для Telemetry DB"
echo "========================================="

# Создаём коннектор для telemetry_db (таблица telemetry_events)
curl -i -X POST -H "Accept:application/json" -H "Content-Type:application/json" \
  http://localhost:8083/connectors/ -d '{
  "name": "telemetry-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "tasks.max": "1",
    "database.hostname": "telemetry-db",
    "database.port": "5432",
    "database.user": "debezium_user",
    "database.password": "debezium_password",
    "database.dbname": "telemetry_db",
    "database.server.name": "telemetry",

    "topic.prefix": "telemetry",
    "plugin.name": "pgoutput",
    "slot.name": "debezium_telemetry",
    "publication.name": "telemetry_debezium_publication",
    "slot.drop.on.stop": "false",
    "snapshot.mode": "initial",
    "snapshot.fetch.size": "1000",

    "schema.include.list": "public",
    "table.include.list": "public.telemetry_events",

    "key.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",

    "key.converter.schemas.enable": "true",
    "value.converter.schemas.enable": "true",

    "provide.transaction.metadata": "false",
    "time.precision.mode": "adaptive_time_microseconds",

    "decimal.handling.mode": "double",
    "heartbeat.interval.ms": "10000",

    "max.batch.size": "2048",
    "poll.interval.ms": "1000",

    "include.schema.changes": "false"
  }
}'

echo ""
echo ""
echo "========================================="
echo "Проверка статуса коннекторов"
echo "========================================="

# Проверяем статус коннекторов
sleep 3
echo ""
echo "Статус CRM-коннектора:"
curl -s http://localhost:8083/connectors/crm-connector/status | jq '.'

echo ""
echo "Статус Telemetry-коннектора:"
curl -s http://localhost:8083/connectors/telemetry-connector/status | jq '.'

echo ""
echo "========================================="
echo "✓ Debezium-коннекторы настроены"
echo "========================================="
echo ""
echo "Kafka-топики:"
echo "  - crm.public.users (изменения в таблице users)"
echo "  - telemetry.public.telemetry_events (изменения в таблице telemetry_events)"
echo ""
echo "Веб-интерфейс Kafdrop: http://localhost:9100"
echo ""
