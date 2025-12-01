# Исправление инициализации схемы debezium в reports_api

## Проблема

При старте `reports_api` не удавалось инициализировать схему `debezium` в ClickHouse из-за того, что ClickHouse ещё не был готов. При этом:

1. В логах писалось `WARNING: Не удалось подключиться к ClickHouse`, но затем `INFO: Схема debezium успешно инициализирована` - что вводило в заблуждение
2. Контейнер продолжал работу, хотя схема не была инициализирована
3. Не было retry-логики для ожидания готовности ClickHouse

## Решение

### 1. Добавлена retry-логика в `init_debezium_schema()`

**Файл:** `reports_api/main.py`

**Изменения:**
- Добавлен цикл с 30 попытками подключения к ClickHouse (с интервалом 2 секунды)
- При каждой попытке проверяется подключение через `SELECT 1`
- Если после 30 попыток подключиться не удалось - выбрасывается `RuntimeError`
- Это приводит к падению контейнера при старте, если ClickHouse недоступен

**Код:**
```python
# Пытаемся подключиться к ClickHouse с retry-логикой
max_attempts = 30
client = None

for attempt in range(1, max_attempts + 1):
    try:
        client = get_clickhouse_client()
        # Проверяем подключение простым запросом
        client.command("SELECT 1")
        logging.info(f"✓ Подключение к ClickHouse установлено (попытка {attempt})")
        break
    except Exception as e:
        if attempt == max_attempts:
            logging.error(f"✗ Не удалось подключиться к ClickHouse после {max_attempts} попыток: {e}")
            raise RuntimeError(f"Не удалось подключиться к ClickHouse для инициализации схемы debezium: {e}")
        
        logging.info(f"Ожидание готовности ClickHouse... (попытка {attempt}/{max_attempts})")
        time.sleep(2)
```

### 2. Добавлены unit-тесты

**Файл:** `reports_api/tests/test_init_debezium_schema.py`

**Тесты:**
1. `test_init_debezium_schema_raises_on_connection_failure` - проверяет, что функция выбрасывает `RuntimeError` при невозможности подключиться
2. `test_init_debezium_schema_retries_connection` - проверяет, что делается 30 попыток подключения
3. `test_init_debezium_schema_succeeds_on_retry` - проверяет, что функция успешно работает, если ClickHouse становится доступным после нескольких попыток
4. `test_init_debezium_schema_skips_if_already_initialized` - проверяет, что повторная инициализация пропускается

### 3. Поведение при ошибках

**До исправления:**
- При недоступности ClickHouse: `WARNING` в логах, контейнер продолжает работу
- Схема `debezium` не инициализируется, но об этом не сообщается явно

**После исправления:**
- При недоступности ClickHouse после 30 попыток (60 секунд): `ERROR` в логах, выбрасывается `RuntimeError`
- Контейнер падает при старте (FastAPI не запускается)
- Docker Compose автоматически перезапускает контейнер (если настроен `restart: always`)
- Благодаря `depends_on: olap-db: condition: service_healthy` в `docker-compose.yaml`, контейнер не запустится, пока ClickHouse не будет готов

## Результаты тестирования

### Unit-тесты
```bash
pytest reports_api/tests/test_init_debezium_schema.py -v
```
✅ **4 passed** - все тесты проходят

### Интеграционные тесты
```bash
pytest tests/test_integration.py -v -k "reports"
```
✅ **2 passed** - тесты `test_reports_api_root` и `test_restart_reports_api_for_debezium_snapshot` проходят

### Тест Debezium CDC
```bash
pytest tests/test_debezium_integration.py -v
```
✅ **1 passed** - интеграционный тест Debezium CDC проходит

## Логи при успешном запуске

```
INFO:root:Инициализация схемы debezium в ClickHouse...
INFO:root:Ожидание готовности ClickHouse... (попытка 1/30)
INFO:root:Ожидание готовности ClickHouse... (попытка 2/30)
INFO:root:✓ Подключение к ClickHouse установлено (попытка 3)
INFO:root:Проверка наличия базы данных debezium...
INFO:root:✓ База данных debezium создана или уже существует
INFO:root:Создание Kafka Engine таблицы для users...
INFO:root:✓ Kafka Engine таблица users_kafka создана
...
INFO:root:✓ Схема debezium полностью инициализирована
INFO:root:Схема debezium успешно инициализирована
```

## Логи при недоступности ClickHouse

```
INFO:root:Инициализация схемы debezium в ClickHouse...
INFO:root:Ожидание готовности ClickHouse... (попытка 1/30)
INFO:root:Ожидание готовности ClickHouse... (попытка 2/30)
...
INFO:root:Ожидание готовности ClickHouse... (попытка 30/30)
ERROR:root:✗ Не удалось подключиться к ClickHouse после 30 попыток: Connection refused
RuntimeError: Не удалось подключиться к ClickHouse для инициализации схемы debezium: Connection refused
```

После этого контейнер падает и не запускается.
