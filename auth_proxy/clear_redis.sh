#!/bin/bash
# Скрипт для полной очистки данных в Redis
# Используется для тестирования auth_proxy

set -e  # Останавливаем выполнение при ошибке

echo "=== Очистка Redis ==="

# Проверяем, запущен ли контейнер redis
if ! docker ps --format '{{.Names}}' | grep -q '^redis$'; then
    echo "✗ Контейнер redis не запущен"
    echo "Запустите docker-compose up -d redis"
    exit 1
fi

echo "✓ Контейнер redis запущен"

# Очищаем все данные в Redis (команда FLUSHALL удаляет все ключи из всех баз данных)
echo "Выполняем FLUSHALL в Redis..."
docker exec redis redis-cli FLUSHALL

echo "✓ Все данные в Redis удалены"
echo "=== Очистка завершена ==="
