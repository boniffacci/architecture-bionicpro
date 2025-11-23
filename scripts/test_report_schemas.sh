#!/bin/bash

# Скрипт для тестирования эндпоинта /report с разными схемами (default и debezium)

set -e

echo "========================================="
echo "Тестирование /report с разными схемами"
echo "========================================="

# Тестовый user_id (берём первого пользователя)
USER_ID=1

echo ""
echo "1. Тестирование с схемой 'default'..."
echo "-------------------------------------------"
RESPONSE_DEFAULT=$(curl -s -X POST http://localhost:3002/report \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": $USER_ID, \"schema\": \"default\"}")

echo "Ответ от /report (schema=default):"
echo "$RESPONSE_DEFAULT" | jq '.'

# Проверяем, что ответ содержит данные
TOTAL_EVENTS_DEFAULT=$(echo "$RESPONSE_DEFAULT" | jq -r '.total_events')
if [ "$TOTAL_EVENTS_DEFAULT" = "null" ] || [ "$TOTAL_EVENTS_DEFAULT" = "0" ]; then
    echo "✗ ОШИБКА: Нет данных в схеме default для user_id=$USER_ID"
    exit 1
else
    echo "✓ Данные в схеме default найдены: $TOTAL_EVENTS_DEFAULT событий"
fi

echo ""
echo "2. Тестирование с схемой 'debezium'..."
echo "-------------------------------------------"
RESPONSE_DEBEZIUM=$(curl -s -X POST http://localhost:3002/report \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": $USER_ID, \"schema\": \"debezium\"}")

echo "Ответ от /report (schema=debezium):"
echo "$RESPONSE_DEBEZIUM" | jq '.'

# Проверяем, что ответ содержит данные
TOTAL_EVENTS_DEBEZIUM=$(echo "$RESPONSE_DEBEZIUM" | jq -r '.total_events')
if [ "$TOTAL_EVENTS_DEBEZIUM" = "null" ] || [ "$TOTAL_EVENTS_DEBEZIUM" = "0" ]; then
    echo "✗ ОШИБКА: Нет данных в схеме debezium для user_id=$USER_ID"
    exit 1
else
    echo "✓ Данные в схеме debezium найдены: $TOTAL_EVENTS_DEBEZIUM событий"
fi

echo ""
echo "3. Тестирование с неправильной схемой..."
echo "-------------------------------------------"
RESPONSE_INVALID=$(curl -s -X POST http://localhost:3002/report \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": $USER_ID, \"schema\": \"invalid\"}")

echo "Ответ от /report (schema=invalid):"
echo "$RESPONSE_INVALID" | jq '.'

# Проверяем, что получили ошибку 400
if echo "$RESPONSE_INVALID" | jq -e '.detail' > /dev/null 2>&1; then
    echo "✓ Получена ожидаемая ошибка для неправильной схемы"
else
    echo "✗ ОШИБКА: Не получена ошибка для неправильной схемы"
    exit 1
fi

echo ""
echo "4. Тестирование без указания схемы (должна использоваться 'default')..."
echo "-------------------------------------------"
RESPONSE_NO_SCHEMA=$(curl -s -X POST http://localhost:3002/report \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": $USER_ID}")

echo "Ответ от /report (без schema):"
echo "$RESPONSE_NO_SCHEMA" | jq '.'

# Проверяем, что ответ содержит данные
TOTAL_EVENTS_NO_SCHEMA=$(echo "$RESPONSE_NO_SCHEMA" | jq -r '.total_events')
if [ "$TOTAL_EVENTS_NO_SCHEMA" = "null" ] || [ "$TOTAL_EVENTS_NO_SCHEMA" = "0" ]; then
    echo "✗ ОШИБКА: Нет данных при использовании схемы по умолчанию"
    exit 1
else
    echo "✓ Данные при использовании схемы по умолчанию найдены: $TOTAL_EVENTS_NO_SCHEMA событий"
fi

echo ""
echo "========================================="
echo "✓ Все тесты пройдены успешно"
echo "========================================="
echo ""
echo "Результаты:"
echo "  - Схема 'default':   $TOTAL_EVENTS_DEFAULT событий"
echo "  - Схема 'debezium':  $TOTAL_EVENTS_DEBEZIUM событий"
echo "  - Без схемы:         $TOTAL_EVENTS_NO_SCHEMA событий"
echo ""
