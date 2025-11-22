#!/bin/bash
# Скрипт для перезапуска ClickHouse с новой конфигурацией

set -e

echo "=== Перезапуск ClickHouse с новой конфигурацией ==="
echo ""

echo "1. Останавливаем контейнер ClickHouse..."
docker compose stop olap_db

echo ""
echo "2. Удаляем старый контейнер..."
docker compose rm -f olap_db

echo ""
echo "3. Запускаем новый контейнер с обновлённой конфигурацией..."
docker compose up -d olap_db

echo ""
echo "4. Ожидаем запуска ClickHouse..."
for i in {1..30}; do
  if docker exec architecture-bionicpro-olap_db-1 clickhouse-client --password clickhouse_password --query "SELECT 1" > /dev/null 2>&1; then
    echo "✓ ClickHouse начал отвечать (попытка $i)"
    sleep 2
    echo "✓ ClickHouse готов к работе"
    break
  fi
  echo "Ожидание ClickHouse... (попытка $i/30)"
  sleep 2
done

echo ""
echo "5. Проверка подключения..."
docker exec architecture-bionicpro-olap_db-1 clickhouse-client --password clickhouse_password --query "SELECT version()"

echo ""
echo "6. Список таблиц:"
docker exec architecture-bionicpro-olap_db-1 clickhouse-client --password clickhouse_password --query "SHOW TABLES"

echo ""
echo "=== ClickHouse успешно перезапущен ==="
echo ""
echo "Параметры подключения для DataGrip:"
echo "  Host: localhost"
echo "  Port: 8123 (HTTP) или 9431 (Native)"
echo "  Database: default"
echo "  User: default"
echo "  Password: clickhouse_password"
echo ""
