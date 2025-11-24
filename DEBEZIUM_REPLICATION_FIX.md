# Исправление репликации данных через Debezium

## Проблема

После запуска `docker compose up -d` и выполнения `populate_base` в `crm_api` и `telemetry_api`, в схеме `debezium` базы данных `olap_db` (ClickHouse) создавались таблицы `users` и `telemetry_events`, но они оставались пустыми.

### Причина

Debezium-коннекторы создавались автоматически при старте контейнера `debezium` (в `Dockerfile` с помощью wrapper-скрипта). Это происходило ДО того, как вызывался `populate_base`, поэтому Debezium делал snapshot пустых таблиц PostgreSQL.

## Решение

### 1. Автоматическая инициализация Debezium-коннекторов в `reports_api`

Добавлена функция `init_debezium_connectors()` в `reports_api/main.py`, которая:
- Удаляет существующие Debezium-коннекторы
- Создаёт новые коннекторы с `snapshot.mode=always`
- Автоматически вызывается при старте `reports_api` в `lifespan`

### 2. Обновление Dockerfile для Debezium

Изменен `debezium/Dockerfile` - убрана автоматическая инициализация коннекторов при старте контейнера. Теперь коннекторы создаются только через `reports_api`.

### 3. Обновление интеграционных тестов

Заменён тест `test_restart_debezium_connectors` на `test_restart_reports_api_for_debezium_snapshot`, который:
- Перезапускает контейнер `reports-api`
- Ждёт автоматической инициализации Debezium-коннекторов
- Проверяет, что данные реплицируются

## Порядок работы после изменений

1. Запустите Docker Compose:
   ```bash
   docker compose down -v
   docker compose build
   docker compose up -d
   ```

2. Дождитесь запуска всех сервисов

3. Заполните базы данных:
   ```bash
   curl -X POST http://localhost:3001/populate_base
   curl -X POST http://localhost:3002/populate_base
   ```

4. **ВАЖНО**: Перезапустите `reports-api` для автоматической инициализации Debezium-коннекторов:
   ```bash
   docker compose restart reports-api
   ```

5. Проверьте данные в ClickHouse:
   ```bash
   docker exec olap-db clickhouse-client --password clickhouse_password \
     --query "SELECT COUNT(*) FROM debezium.users"
   
   docker exec olap-db clickhouse-client --password clickhouse_password \
     --query "SELECT COUNT(*) FROM debezium.telemetry_events"
   ```

## Автоматизация

Вместо ручного перезапуска `reports-api`, можно использовать интеграционные тесты:

```bash
# Запуск полного набора тестов с автоматической инициализацией Debezium
uv run pytest tests/test_integration.py::test_populate_crm_database \
  tests/test_integration.py::test_populate_telemetry_database \
  tests/test_integration.py::test_restart_reports_api_for_debezium_snapshot \
  tests/test_integration.py::test_debezium_users_data_replicated \
  tests/test_integration.py::test_debezium_telemetry_data_replicated -v
```

## Как это работает

1. При старте `reports-api` вызывается `lifespan`, который:
   - Инициализирует MinIO-клиент
   - Создаёт схему `debezium` в ClickHouse (Kafka Engine таблицы и Materialized Views)
   - **Пересоздаёт Debezium-коннекторы** для snapshot существующих данных
   - Импортирует данные в схему `default` (если необходимо)

2. Debezium-коннекторы с `snapshot.mode=always`:
   - Делают полный snapshot всех существующих данных в PostgreSQL
   - Отправляют их в Kafka-топики
   - ClickHouse читает данные из Kafka и сохраняет в таблицы `debezium.users` и `debezium.telemetry_events`

3. В дальнейшем Debezium отслеживает изменения в реальном времени (CDC)

## Проверка работоспособности

Запустите интеграционные тесты:

```bash
uv run pytest tests/test_integration.py -v
```

Все тесты должны пройти успешно, включая:
- ✅ `test_debezium_users_data_replicated` - проверка репликации пользователей
- ✅ `test_debezium_telemetry_data_replicated` - проверка репликации событий
- ✅ `test_data_consistency_between_postgres_and_clickhouse` - проверка консистентности данных
