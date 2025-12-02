#!/bin/bash

# Скрипт для тестирования создания отчётов и их сохранения в MinIO

echo "=== Тест создания отчётов и сохранения в MinIO ==="
echo

# Получаем JWT-токен
echo "1. Получение JWT-токена..."
TOKEN=$(curl -s -X POST http://localhost:8080/realms/reports-realm/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=reports-frontend" \
  -d "username=prosthetic1" \
  -d "password=prosthetic123" \
  -d "grant_type=password" | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "✗ Ошибка: не удалось получить токен"
  exit 1
fi
echo "✓ Токен получен"
echo

# Создаём отчёт для схемы default
echo "2. Создание отчёта (default)..."
REPORT_DEFAULT=$(curl -s -X POST http://localhost:3003/reports \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "start_ts": null,
    "end_ts": "2025-12-01T00:00:00",
    "schema": "default"
  }')

USER_NAME=$(echo "$REPORT_DEFAULT" | jq -r '.user_name // "ERROR"')
if [ "$USER_NAME" = "ERROR" ]; then
  echo "✗ Ошибка при создании отчёта (default)"
  echo "$REPORT_DEFAULT"
  exit 1
fi
echo "✓ Отчёт создан для пользователя: $USER_NAME"
echo

# Создаём отчёт для схемы debezium
echo "3. Создание отчёта (debezium)..."
REPORT_DEBEZIUM=$(curl -s -X POST http://localhost:3003/reports \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "start_ts": null,
    "end_ts": "2025-12-01T00:00:00",
    "schema": "debezium"
  }')

USER_NAME=$(echo "$REPORT_DEBEZIUM" | jq -r '.user_name // "ERROR"')
if [ "$USER_NAME" = "ERROR" ]; then
  echo "✗ Ошибка при создании отчёта (debezium)"
  echo "$REPORT_DEBEZIUM"
  exit 1
fi
echo "✓ Отчёт создан для пользователя: $USER_NAME"
echo

# Проверяем файлы в MinIO
echo "4. Проверка файлов в MinIO..."
FILES=$(docker exec minio mc ls local/reports --recursive)
echo "$FILES"
echo

# Подсчитываем количество файлов
FILE_COUNT=$(echo "$FILES" | grep -c "\.json")
if [ "$FILE_COUNT" -ge 2 ]; then
  echo "✓ В MinIO найдено $FILE_COUNT файл(ов)"
else
  echo "✗ Ошибка: в MinIO должно быть минимум 2 файла, найдено: $FILE_COUNT"
  exit 1
fi
echo

# Проверяем доступ к файлам через minio-nginx
echo "5. Проверка доступа к файлам через minio-nginx..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:9002/reports/default/54885c9b-6eea-48f7-89f9-353ad8273e95/none__2025-12-01T00-00-00.json \
  -H "Authorization: Bearer $TOKEN")

if [ "$HTTP_CODE" = "200" ]; then
  echo "✓ Файл доступен через minio-nginx (HTTP $HTTP_CODE)"
else
  echo "✗ Ошибка доступа к файлу через minio-nginx (HTTP $HTTP_CODE)"
  exit 1
fi
echo

echo "=== Все тесты пройдены успешно! ==="
echo
echo "Теперь можете открыть http://localhost:3000 в браузере,"
echo "войти под prosthetic1:prosthetic123 и нажать кнопки 'Отчёт (default)' и 'Отчёт (debezium)'."
echo "Отчёты должны загружаться из MinIO кэша."
