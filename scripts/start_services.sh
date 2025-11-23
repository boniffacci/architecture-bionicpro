#!/bin/bash

# Скрипт для запуска всех микросервисов

set -e

echo "========================================="
echo "Запуск микросервисов"
echo "========================================="

# Проверяем, что Docker Compose запущен
echo "Проверка Docker Compose..."
if ! docker compose ps | grep -q "Up"; then
    echo "✗ Docker Compose не запущен"
    echo "Запустите: docker compose up -d"
    exit 1
fi
echo "✓ Docker Compose запущен"

# Запускаем CRM API в фоне
echo ""
echo "Запуск CRM API (порт 3001)..."
cd "$(dirname "$0")/.."
uv run python -m crm_api.main > /tmp/crm_api.log 2>&1 &
CRM_PID=$!
echo "✓ CRM API запущен (PID: $CRM_PID)"

# Запускаем Telemetry API в фоне
echo ""
echo "Запуск Telemetry API (порт 3001)..."
uv run python -m telemetry_api.main > /tmp/telemetry_api.log 2>&1 &
TELEMETRY_PID=$!
echo "✓ Telemetry API запущен (PID: $TELEMETRY_PID)"

# Ждём запуска сервисов
echo ""
echo "Ожидание запуска сервисов..."
sleep 5

# Проверяем доступность
echo ""
echo "Проверка доступности сервисов..."
for i in {1..30}; do
  if curl -s -f http://localhost:3001/health > /dev/null 2>&1; then
    echo "✓ CRM API доступен"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "✗ CRM API не запустился"
    kill $CRM_PID 2>/dev/null || true
    kill $TELEMETRY_PID 2>/dev/null || true
    exit 1
  fi
  sleep 1
done

for i in {1..30}; do
  if curl -s -f http://localhost:3001/health > /dev/null 2>&1; then
    echo "✓ Telemetry API доступен"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "✗ Telemetry API не запустился"
    kill $CRM_PID 2>/dev/null || true
    kill $TELEMETRY_PID 2>/dev/null || true
    exit 1
  fi
  sleep 1
done

echo ""
echo "========================================="
echo "✓ Все микросервисы запущены"
echo "========================================="
echo ""
echo "PID файлы:"
echo "  CRM API: $CRM_PID"
echo "  Telemetry API: $TELEMETRY_PID"
echo ""
echo "Логи:"
echo "  CRM API: /tmp/crm_api.log"
echo "  Telemetry API: /tmp/telemetry_api.log"
echo ""
echo "Для остановки:"
echo "  kill $CRM_PID $TELEMETRY_PID"
echo ""

# Сохраняем PID в файлы
echo $CRM_PID > /tmp/crm_api.pid
echo $TELEMETRY_PID > /tmp/telemetry_api.pid
