#!/bin/bash
# Wrapper-скрипт для автоматического запуска Debezium Connect и инициализации коннекторов

set -e

echo "========================================="
echo "Запуск Debezium Connect"
echo "========================================="

# Запускаем стандартный Kafka Connect в фоне
/docker-entrypoint.sh start &
CONNECT_PID=$!

# Даём время на инициализацию Kafka Connect (чтобы REST API стал доступен)
echo "Ожидание запуска Kafka Connect REST API..."
for i in {1..60}; do
  if curl -s -f http://localhost:8083/ > /dev/null 2>&1; then
    echo "✓ Kafka Connect REST API запущен (попытка $i)"
    break
  fi
  echo "Ожидание... (попытка $i/60)"
  sleep 2
done

# Проверяем, что Kafka Connect доступен
if ! curl -s -f http://localhost:8083/ > /dev/null 2>&1; then
  echo "✗ Kafka Connect REST API не запустился"
  exit 1
fi

# Даём дополнительное время на инициализацию (чтобы все топики и настройки были готовы)
echo "Дополнительная пауза для полной инициализации..."
sleep 10

# Запускаем скрипт инициализации коннекторов
echo ""
echo "========================================="
echo "Запуск инициализации Debezium-коннекторов"
echo "========================================="
/usr/local/bin/init_debezium_connectors.sh &

# Ждём завершения процесса Kafka Connect
wait $CONNECT_PID
