#!/bin/bash

# Скрипт для тестирования интеграции Kafka + Debezium + ClickHouse

set -e

echo "========================================="
echo "Тестирование Kafka + Debezium + ClickHouse"
echo "========================================="

# Параметры подключения к ClickHouse
CLICKHOUSE_HOST="localhost"
CLICKHOUSE_PORT="8123"
CLICKHOUSE_USER="default"
CLICKHOUSE_PASSWORD="clickhouse_password"

# Функция для выполнения SQL-запросов в ClickHouse
clickhouse_query() {
    local query="$1"
    curl -s "http://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/" \
        --user "${CLICKHOUSE_USER}:${CLICKHOUSE_PASSWORD}" \
        --data-binary "${query}"
}

echo ""
echo "1. Проверка наличия схемы debezium в ClickHouse..."
echo "-------------------------------------------"
echo "Список баз данных:"
clickhouse_query "SHOW DATABASES"

echo ""
echo "Проверка наличия базы debezium:"
DB_EXISTS=$(clickhouse_query "SELECT count() FROM system.databases WHERE name = 'debezium'")
if [ "$DB_EXISTS" -eq "0" ]; then
    echo "✗ База данных debezium НЕ НАЙДЕНА!"
    echo "Запустите: ./scripts/setup_clickhouse_kafka.sh"
    exit 1
else
    echo "✓ База данных debezium найдена"
fi

echo ""
echo "Список таблиц в схеме debezium:"
clickhouse_query "SHOW TABLES FROM debezium"

echo ""
echo "2. Проверка статуса Debezium-коннекторов..."
echo "-------------------------------------------"
echo "CRM-коннектор:"
curl -s http://localhost:8083/connectors/crm-connector/status | jq '.connector.state, .tasks[0].state'

echo ""
echo "Telemetry-коннектор:"
curl -s http://localhost:8083/connectors/telemetry-connector/status | jq '.connector.state, .tasks[0].state'

echo ""
echo "3. Проверка Kafka-топиков через Kafdrop..."
echo "-------------------------------------------"
echo "Веб-интерфейс Kafdrop: http://localhost:9100"
echo "Ожидаемые топики:"
echo "  - crm.public.users"
echo "  - telemetry.public.telemetry_events"

echo ""
echo "4. Наполнение CRM DB тестовыми данными..."
echo "-------------------------------------------"
curl -s -X POST http://localhost:3002/populate_base | jq '.status, .users_loaded'

echo ""
echo "5. Наполнение Telemetry DB тестовыми данными..."
echo "-------------------------------------------"
curl -s -X POST http://localhost:3003/populate_base | jq '.status, .events_loaded'

echo ""
echo "6. Ожидание репликации данных через Debezium..."
echo "-------------------------------------------"
echo "Ожидаем появления данных в ClickHouse (максимум 60 секунд)..."

# Ожидание данных в users_join
for i in {1..30}; do
    USERS_COUNT=$(clickhouse_query "SELECT count() FROM debezium.users_join" 2>/dev/null || echo "0")
    if [ "$USERS_COUNT" -gt "0" ]; then
        echo "✓ Данные в debezium.users_join появились (попытка $i, количество: $USERS_COUNT)"
        break
    fi
    echo "Ожидание данных в debezium.users_join... (попытка $i/30)"
    sleep 2
done

# Ожидание данных в telemetry_events_merge
for i in {1..30}; do
    EVENTS_COUNT=$(clickhouse_query "SELECT count() FROM debezium.telemetry_events_merge" 2>/dev/null || echo "0")
    if [ "$EVENTS_COUNT" -gt "0" ]; then
        echo "✓ Данные в debezium.telemetry_events_merge появились (попытка $i, количество: $EVENTS_COUNT)"
        break
    fi
    echo "Ожидание данных в debezium.telemetry_events_merge... (попытка $i/30)"
    sleep 2
done

echo ""
echo "7. Проверка данных в ClickHouse (схема debezium)..."
echo "-------------------------------------------"

echo ""
echo "Количество пользователей в debezium.users_join:"
USERS_COUNT=$(clickhouse_query "SELECT count() FROM debezium.users_join")
echo "$USERS_COUNT"

if [ "$USERS_COUNT" -eq "0" ]; then
    echo "✗ ОШИБКА: Данные в debezium.users_join НЕ ПОЯВИЛИСЬ!"
    echo "Проверьте:"
    echo "  1. Статус Debezium-коннектора: curl http://localhost:8083/connectors/crm-connector/status"
    echo "  2. Kafka-топики в Kafdrop: http://localhost:9100"
    echo "  3. Логи ClickHouse: docker compose logs clickhouse"
    exit 1
else
    echo "✓ Данные в debezium.users_join найдены: $USERS_COUNT записей"
fi

echo ""
echo "Первые 5 пользователей из debezium.users_join:"
clickhouse_query "SELECT user_id, name, email FROM debezium.users_join LIMIT 5 FORMAT Pretty"

echo ""
echo "Количество событий в debezium.telemetry_events_merge:"
EVENTS_COUNT=$(clickhouse_query "SELECT count() FROM debezium.telemetry_events_merge")
echo "$EVENTS_COUNT"

if [ "$EVENTS_COUNT" -eq "0" ]; then
    echo "✗ ОШИБКА: Данные в debezium.telemetry_events_merge НЕ ПОЯВИЛИСЬ!"
    echo "Проверьте:"
    echo "  1. Статус Debezium-коннектора: curl http://localhost:8083/connectors/telemetry-connector/status"
    echo "  2. Kafka-топики в Kafdrop: http://localhost:9100"
    echo "  3. Логи ClickHouse: docker compose logs clickhouse"
    exit 1
else
    echo "✓ Данные в debezium.telemetry_events_merge найдены: $EVENTS_COUNT записей"
fi

echo ""
echo "Первые 5 событий из debezium.telemetry_events_merge:"
clickhouse_query "SELECT id, event_uuid, user_id, prosthesis_type, created_ts FROM debezium.telemetry_events_merge LIMIT 5 FORMAT Pretty"

echo ""
echo "========================================="
echo "✓ Тестирование завершено УСПЕШНО"
echo "========================================="
echo ""
echo "Интеграция Kafka + Debezium + ClickHouse работает корректно!"
echo "  - Пользователей в ClickHouse: $USERS_COUNT"
echo "  - Событий в ClickHouse: $EVENTS_COUNT"
echo ""
