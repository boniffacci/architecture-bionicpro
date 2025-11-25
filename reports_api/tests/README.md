# Тесты для Reports API

## Интеграционные тесты Debezium CDC

Файл: `test_debezium_integration.py`

### Описание

Набор интеграционных тестов для проверки работы Debezium CDC (Change Data Capture) и репликации данных из PostgreSQL в ClickHouse.

### Что проверяют тесты

1. **Инфраструктура Debezium**
   - Debezium Kafka Connect запущен и доступен
   - Debezium-коннекторы созданы (crm-connector, telemetry-connector)
   - Коннекторы работают в состоянии RUNNING

2. **Схема ClickHouse**
   - Схема `debezium` создана
   - Все необходимые таблицы созданы:
     - `users_kafka` (Kafka Engine)
     - `users` (Join Engine)
     - `users_mv` (Materialized View)
     - `telemetry_events_kafka` (Kafka Engine)
     - `telemetry_events` (ReplacingMergeTree)
     - `telemetry_events_mv` (Materialized View)

3. **Данные в PostgreSQL**
   - В CRM DB есть данные пользователей
   - В Telemetry DB есть данные событий телеметрии

4. **Репликация данных**
   - Данные из CRM DB реплицируются в `debezium.users`
   - Данные из Telemetry DB реплицируются в `debezium.telemetry_events`
   - Количество записей совпадает между PostgreSQL и ClickHouse

5. **Репликация в реальном времени**
   - Новые записи в PostgreSQL автоматически реплицируются в ClickHouse

### Запуск тестов

```bash
# Запуск всех тестов
uv run pytest reports_api/test_debezium_integration.py -v

# Запуск с подробным выводом
uv run pytest reports_api/test_debezium_integration.py -v -s

# Запуск конкретного теста
uv run pytest reports_api/test_debezium_integration.py::test_clickhouse_users_data_replicated -v -s
```

### Требования

Перед запуском тестов убедитесь, что:

1. Все сервисы запущены через `docker compose up -d`
2. Debezium-коннекторы созданы (автоматически при старте или через `bash scripts/setup_debezium_connectors.sh`)
3. В PostgreSQL есть тестовые данные

### Конфигурация

Тесты используют следующие параметры подключения:

- **ClickHouse**: `localhost:8123`, пользователь `default`, пароль `clickhouse_password`
- **CRM DB**: `localhost:5444`, пользователь `crm_user`, пароль `crm_password`
- **Telemetry DB**: `localhost:5445`, пользователь `telemetry_user`, пароль `telemetry_password`
- **Debezium API**: `http://localhost:8083`

### Результаты тестов

При успешном прохождении всех тестов вы увидите:

```
✓ Debezium Kafka Connect запущен и доступен
✓ Debezium-коннекторы созданы: ['crm-connector', 'telemetry-connector']
✓ CRM-коннектор работает: RUNNING
✓ Telemetry-коннектор работает: RUNNING
✓ Схема debezium существует в ClickHouse
✓ Все необходимые таблицы созданы
✓ В CRM DB есть 1000 пользователей
✓ В Telemetry DB есть 10000 событий
✓ В debezium.users реплицировано 1000 пользователей
✓ В debezium.telemetry_events реплицировано 10000 событий
✓ Консистентность данных users: PostgreSQL=1000, ClickHouse=1000
✓ Консистентность данных telemetry_events: PostgreSQL=10000, ClickHouse=10000
✓ Новый пользователь реплицирован в ClickHouse

============================== 12 passed in 2.30s ==============================
```

### Устранение проблем

#### Тесты не проходят из-за отсутствия коннекторов

Если коннекторы не созданы автоматически при старте Debezium, создайте их вручную:

```bash
bash scripts/setup_debezium_connectors.sh
```

#### Данные не реплицируются

1. Проверьте статус коннекторов:
   ```bash
   curl http://localhost:8083/connectors/crm-connector/status | jq .
   curl http://localhost:8083/connectors/telemetry-connector/status | jq .
   ```

2. Проверьте логи Debezium:
   ```bash
   docker logs debezium --tail 100
   ```

3. Проверьте Kafka-топики в Kafdrop: http://localhost:9100

#### Таблицы в ClickHouse пусты

1. Убедитесь, что Kafka Engine таблицы работают:
   ```bash
   docker exec olap-db clickhouse-client --password=clickhouse_password \
     --query="SELECT * FROM system.kafka_consumers"
   ```

2. Проверьте Materialized Views:
   ```bash
   docker exec olap-db clickhouse-client --password=clickhouse_password \
     --query="SHOW CREATE TABLE debezium.users_mv"
   ```

### Дополнительная информация

- Документация Debezium: https://debezium.io/documentation/
- Документация ClickHouse Kafka Engine: https://clickhouse.com/docs/en/engines/table-engines/integrations/kafka
