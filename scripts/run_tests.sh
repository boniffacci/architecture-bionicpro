#!/bin/bash
# Скрипт для запуска E2E тестов

# Переходим в корневую директорию проекта
cd "$(dirname "$0")/.." || exit 1

echo "=== Запуск E2E тестов ==="
echo ""

# Проверяем, что все сервисы запущены
echo "Проверка доступности сервисов..."

# Проверяем Keycloak
if ! curl -s -f http://localhost:8080/realms/reports-realm > /dev/null 2>&1; then
  echo "✗ Keycloak недоступен на http://localhost:8080"
  echo "  Запустите сервисы: ./scripts/run_all_services.sh"
  exit 1
fi
echo "✓ Keycloak доступен"

# Проверяем Redis
if ! docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
  echo "✗ Redis недоступен"
  echo "  Запустите сервисы: ./scripts/run_all_services.sh"
  exit 1
fi
echo "✓ Redis доступен"

# Проверяем reports_api
if ! curl -s -f http://localhost:3001/jwt > /dev/null 2>&1; then
  echo "✗ reports_api недоступен на http://localhost:3001"
  echo "  Запустите сервисы: ./scripts/run_all_services.sh"
  exit 1
fi
echo "✓ reports_api доступен"

# Проверяем auth_proxy
if ! curl -s -f http://localhost:3002/health > /dev/null 2>&1; then
  echo "✗ auth_proxy недоступен на http://localhost:3002"
  echo "  Запустите сервисы: ./scripts/run_all_services.sh"
  exit 1
fi
echo "✓ auth_proxy доступен"

# Проверяем фронтенд
if ! curl -s -f http://localhost:5173 > /dev/null 2>&1; then
  echo "✗ Фронтенд недоступен на http://localhost:5173"
  echo "  Запустите сервисы: ./scripts/run_all_services.sh"
  exit 1
fi
echo "✓ Фронтенд доступен"

echo ""
echo "Все сервисы доступны, запускаем тесты..."
echo ""

# Запускаем тесты
uv run pytest tests/test_e2e_auth_proxy.py -v -s

echo ""
echo "=== Тесты завершены ==="
