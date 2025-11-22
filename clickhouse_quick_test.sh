#!/bin/bash
# Быстрая проверка подключения к ClickHouse

echo "=== Проверка подключения к ClickHouse ==="
echo ""

echo "1. Версия ClickHouse:"
curl -s "http://localhost:8123/?query=SELECT%20version()"
echo ""
echo ""

echo "2. Список таблиц:"
curl -s "http://localhost:8123/?query=SHOW%20TABLES"
echo ""
echo ""

echo "3. Количество пользователей:"
curl -s "http://localhost:8123/?query=SELECT%20COUNT(*)%20FROM%20users"
echo ""
echo ""

echo "4. Количество событий телеметрии:"
curl -s "http://localhost:8123/?query=SELECT%20COUNT(*)%20FROM%20telemetry_events"
echo ""
echo ""

echo "5. Топ-5 пользователей по количеству событий:"
curl -s "http://localhost:8123/?query=SELECT%20u.name,%20COUNT(t.id)%20as%20cnt%20FROM%20telemetry_events%20t%20JOIN%20users%20u%20ON%20t.user_id%20=%20u.user_id%20GROUP%20BY%20u.name%20ORDER%20BY%20cnt%20DESC%20LIMIT%205&default_format=PrettyCompact"
echo ""
echo ""

echo "=== Параметры подключения для DataGrip ==="
echo "Host: localhost"
echo "Port (HTTP): 8123"
echo "Port (Native): 9431"
echo "Database: default"
echo "User: default"
echo "Password: (пустой)"
echo ""
