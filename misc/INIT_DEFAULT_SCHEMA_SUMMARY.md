# Резюме: Инициализация схемы default при запуске reports_api

## Задача
Добавить автоматическое создание Clickhouse-таблиц в схеме `default` при запуске `reports_api`, не дожидаясь первого вызова `/reports`.

## Реализация

### 1. Добавлена функция `init_default_schema()` в `reports_api/main.py`

Функция выполняет следующие действия:
- Подключается к ClickHouse с retry-логикой (30 попыток с интервалом 2 секунды)
- Создаёт базу данных `default` (если не существует)
- Создаёт таблицу `default.users` с движком `Join(ANY, LEFT, user_uuid)`
- Создаёт таблицу `default.telemetry_events` с движком `ReplacingMergeTree(saved_ts)`
- Проверяет существование таблиц перед созданием (идемпотентность)

### 2. Интеграция в lifespan

Функция `init_default_schema()` вызывается в `lifespan` context manager при запуске приложения:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: инициализация MinIO
    init_minio()
    
    # Startup: инициализация схемы default в ClickHouse
    init_default_schema()  # <-- НОВОЕ
    
    # Startup: инициализация схемы debezium в ClickHouse
    init_debezium_schema()
    
    # ... остальная инициализация
```

### 3. Структура таблиц

#### Таблица `default.users`
```sql
CREATE TABLE default.users (
    user_id Int32,
    user_uuid String,
    name String,
    email String,
    age Nullable(Int32),
    gender Nullable(String),
    country Nullable(String),
    address Nullable(String),
    phone Nullable(String),
    registered_at DateTime
) ENGINE = Join(ANY, LEFT, user_uuid)
```

#### Таблица `default.telemetry_events`
```sql
CREATE TABLE default.telemetry_events (
    id Int64,
    event_uuid String,
    user_uuid String,
    prosthesis_type String,
    muscle_group String,
    signal_frequency Int32,
    signal_duration Int32,
    signal_amplitude Float64,
    created_ts DateTime,
    saved_ts DateTime
) ENGINE = ReplacingMergeTree(saved_ts)
PARTITION BY (toYear(created_ts), toMonth(created_ts))
ORDER BY (user_uuid, event_uuid, created_ts)
```

## Тестирование

### Unit-тесты (`reports_api/tests/test_init_default_schema.py`)

Созданы 7 unit-тестов для проверки функции `init_default_schema()`:
1. `test_init_default_schema_raises_on_connection_failure` - проверка выброса RuntimeError при недоступности ClickHouse
2. `test_init_default_schema_retries_connection` - проверка retry-логики (30 попыток)
3. `test_init_default_schema_succeeds_on_retry` - проверка успешного подключения после нескольких попыток
4. `test_init_default_schema_creates_users_table` - проверка создания таблицы users
5. `test_init_default_schema_creates_telemetry_events_table` - проверка создания таблицы telemetry_events
6. `test_init_default_schema_skips_existing_tables` - проверка пропуска существующих таблиц
7. `test_init_default_schema_creates_only_missing_tables` - проверка создания только отсутствующих таблиц

**Результат**: ✅ Все 7 тестов прошли успешно

### Интеграционный тест (`tests/test_default_schema_creation.py`)

Создан интеграционный тест, который:
1. Удаляет таблицы из схемы `default`
2. Перезапускает `reports-api`
3. Проверяет, что таблицы созданы при запуске
4. Проверяет структуру созданных таблиц

**Результат**: ✅ Тест прошёл успешно

## Результаты

### До изменений
- Таблицы в схеме `default` создавались только при импорте данных через DAG Airflow
- При первом запуске `reports_api` таблиц не было

### После изменений
- Таблицы в схеме `default` создаются автоматически при запуске `reports_api`
- Приложение готово к работе сразу после запуска
- Идемпотентность: повторный запуск не пересоздаёт таблицы

### Логи запуска
```
INFO:root:Инициализация схемы default в ClickHouse...
INFO:root:✓ Подключение к ClickHouse установлено (попытка 1)
INFO:root:Проверка наличия базы данных default...
INFO:root:✓ База данных default создана или уже существует
INFO:root:Создание таблицы default.users...
INFO:root:✓ Таблица default.users создана
INFO:root:Создание таблицы default.telemetry_events...
INFO:root:✓ Таблица default.telemetry_events создана
INFO:root:✓ Схема default полностью инициализирована
INFO:root:Схема default успешно инициализирована
```

## Совместимость

- ✅ Совместимо с существующей схемой `debezium`
- ✅ Совместимо с ETL-процессом Airflow
- ✅ Не ломает существующие тесты
- ✅ Идемпотентно (можно запускать многократно)

## Файлы изменений

1. **reports_api/main.py** - добавлена функция `init_default_schema()` и её вызов в `lifespan`
2. **reports_api/tests/test_init_default_schema.py** - unit-тесты для функции
3. **tests/test_default_schema_creation.py** - интеграционный тест

## Статус
✅ **Задача выполнена**: `reports_api` теперь создаёт Clickhouse-таблицы в схеме `default` сразу при запуске, не дожидаясь первого вызова `/reports`.
