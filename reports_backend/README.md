# Reports Backend API

Микросервис для генерации отчетов на основе данных из ClickHouse OLAP БД.

## Структура

- `main.py` - основной модуль FastAPI с эндпоинтами
- `import_olap_data.py` - скрипт для импорта данных из CRM и Telemetry БД в ClickHouse
- `olap_query_examples.py` - примеры запросов к ClickHouse через SQLAlchemy
- `test_import_olap_data.py` - тесты для скрипта импорта
- `test_report_endpoint.py` - тесты для эндпоинта /report

## Зависимости

Для работы требуется:
- PostgreSQL (CRM DB на порту 5444, Telemetry DB на порту 5445)
- ClickHouse (на порту 8123)
- Python 3.12+

## Импорт данных в ClickHouse

### Полный импорт всех данных

```bash
uv run python reports_backend/import_olap_data.py
```

### Импорт с фильтрацией по времени

```bash
# Импорт телеметрии только за март 2025
uv run python reports_backend/import_olap_data.py \
  --telemetry_start_ts="2025-03-01 00:00:00" \
  --telemetry_end_ts="2025-04-01 00:00:00"
```

### Использование как модуля

```python
from reports_backend.import_olap_data import main
from datetime import datetime

# Полный импорт
main()

# Импорт с фильтрами
main(
    telemetry_start_ts=datetime(2025, 3, 1),
    telemetry_end_ts=datetime(2025, 3, 31)
)
```

## Структура данных в ClickHouse

### Таблица `users` (Join Table Engine)

- `user_id` (Int32) - ID пользователя
- `user_uuid` (String) - UUID пользователя (формат Keycloak)
- `name` (String) - имя пользователя
- `email` (String) - email
- `age` (Nullable(Int32)) - возраст
- `gender` (Nullable(String)) - пол
- `country` (Nullable(String)) - страна
- `address` (Nullable(String)) - адрес
- `phone` (Nullable(String)) - телефон
- `registration_ts` (DateTime) - дата регистрации пользователя
- `registered_at` (DateTime) - дата добавления записи в БД

**Индексация**: PRIMARY KEY = `user_id`, индексы по `user_uuid` и `registration_ts`

### Таблица `telemetry_events` (MergeTree)

- `id` (Int64) - ID события
- `user_id` (Int32) - ID пользователя
- `prosthesis_type` (String) - тип протеза (arm, hand, leg)
- `muscle_group` (String) - группа мышц
- `signal_frequency` (Int32) - частота сигнала (Гц)
- `signal_duration` (Int32) - длительность сигнала (мс)
- `signal_amplitude` (Float64) - амплитуда сигнала
- `signal_time` (DateTime) - время снятия сигнала
- `saved_ts` (DateTime) - время сохранения в БД

**Партиционирование**: по году и месяцу `signal_time`  
**Сортировка**: `ORDER BY (user_id, signal_time)`

## API Эндпоинты

### POST /report

Генерирует отчет по пользователю за указанный период.

**Запрос:**

```json
{
  "user_id": 512,
  "start_ts": "2025-03-01T00:00:00",  // опционально
  "end_ts": "2025-03-31T23:59:59"     // опционально
}
```

**Ответ:**

```json
{
  "user_name": "Alexis Moore",
  "user_email": "alexis.moore@example.com",
  "total_events": 150,
  "total_duration": 450000,
  "prosthesis_stats": [
    {
      "prosthesis_type": "arm",
      "events_count": 100,
      "total_duration": 300000,
      "avg_amplitude": 3.45,
      "avg_frequency": 250.5
    },
    {
      "prosthesis_type": "hand",
      "events_count": 50,
      "total_duration": 150000,
      "avg_amplitude": 2.89,
      "avg_frequency": 180.2
    }
  ]
}
```

## Примеры запросов к OLAP БД

Запустить примеры:

```bash
uv run python reports_backend/olap_query_examples.py
```

Примеры включают:
1. Общее количество пользователей
2. Общее количество событий
3. События по конкретному пользователю
4. События по месяцам
5. Средняя амплитуда и частота по типам протезов
6. Детальный отчет по пользователю
7. Топ самых активных пользователей
8. Распределение событий по группам мышц

## Запуск тестов

### Тесты импорта данных

```bash
uv run pytest reports_backend/test_import_olap_data.py -v
```

### Тесты эндпоинта /report

```bash
uv run pytest reports_backend/test_report_endpoint.py -v
```

### Все тесты

```bash
uv run pytest reports_backend/ -v
```

## Запуск сервера

```bash
uv run python reports_backend/main.py
```

Сервер будет доступен на `http://localhost:3001`

## Логика работы import_olap_data

1. **Подключение к ClickHouse** - проверка доступности OLAP БД
2. **Создание таблиц** - если таблицы не существуют, они создаются
3. **Импорт пользователей** - полная перезаливка данных из CRM DB
4. **Импорт телеметрии** - загрузка событий с учетом временных фильтров
5. **Удаление старых данных** - события из указанного интервала удаляются перед вставкой новых
6. **Очистка orphaned events** - удаление событий для пользователей, которых больше нет в БД

## Особенности реализации

- **Asyncio-подход**: все операции используют асинхронные вызовы
- **Партиционирование**: телеметрия партиционирована по году и месяцу для быстрого поиска
- **Join Table Engine**: таблица пользователей использует Join Engine для быстрых JOIN-операций
- **Инкрементальная загрузка**: поддержка загрузки только новых данных за период
- **Автоматическая очистка**: удаление orphaned events при каждом импорте
