#!/bin/bash
# Скрипт для проверки, что данные проходят через Debezium в ClickHouse

set -e

echo "=== Тест потока данных через Debezium ==="
echo ""

# 1. Создаём тестового пользователя через CRM API
echo "1. Создание тестового пользователя через CRM API..."
TIMESTAMP=$(date +%s)
EMAIL="test-$TIMESTAMP@debezium.com"
RESPONSE=$(curl -s -X POST http://localhost:3001/register \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"test_user_$TIMESTAMP\",
    \"email\": \"$EMAIL\",
    \"name\": \"Test User\",
    \"age\": 25,
    \"country\": \"Test Country\"
  }")

echo "   Ответ: $RESPONSE"

# Извлекаем user_uuid из ответа
USER_UUID=$(echo "$RESPONSE" | jq -r '.user_uuid')
echo "   UUID пользователя: $USER_UUID"
echo ""

# 2. Ждём, пока данные появятся в Kafka (через Debezium)
echo "2. Ожидание появления данных в Kafka..."
sleep 5
echo "   ✓ Данные должны быть в Kafka топике crm.public.users"
echo ""

# 3. Инициализируем схему debezium в ClickHouse (если ещё не создана)
echo "3. Инициализация схемы debezium в ClickHouse..."
uv run python -c "
import sys
sys.path.insert(0, 'reports_api')
from main import init_debezium_schema
init_debezium_schema()
print('   ✓ Схема debezium инициализирована')
"
echo ""

# 4. Ждём, пока данные появятся в ClickHouse (через Kafka Engine)
echo "4. Проверка появления данных в ClickHouse (ожидание до 60 секунд)..."
for i in {1..30}; do
  COUNT=$(docker exec olap-db clickhouse-client --password clickhouse_password \
    --query "SELECT COUNT(*) FROM debezium.users WHERE user_uuid = '$USER_UUID'" 2>/dev/null || echo "0")
  
  if [ "$COUNT" -gt 0 ]; then
    echo "   ✓ Данные найдены в debezium.users (попытка $i)"
    echo ""
    
    # Показываем данные
    echo "5. Данные в ClickHouse:"
    docker exec olap-db clickhouse-client --password clickhouse_password \
      --query "SELECT * FROM debezium.users WHERE user_uuid = '$USER_UUID' FORMAT Vertical"
    echo ""
    
    echo "=== ✓ Тест успешно пройден! Данные прошли через Debezium в ClickHouse ==="
    exit 0
  fi
  
  echo "   Попытка $i/30: данные ещё не появились, ожидание 2 сек..."
  sleep 2
done

echo "   ✗ Данные не появились в ClickHouse за 60 секунд"
echo ""
echo "=== ✗ Тест провален ==="
exit 1
