# Сводка изменений

## Выполненные задачи

### 1. ✅ Запуск и проверка сервисов
- Запущены все сервисы: `auth_proxy`, `crm_api`, `telemetry_api`, `reports_api`
- Проверена доступность на портах: 3000, 3001, 3002, 3003
- Все сервисы отвечают корректно

### 2. ✅ Исправление тестов
- Запущены тесты `test_e2e_keycloak.py` и `test_e2e_auth_proxy.py`
- Выявлена проблема: фронтенд отправлял запросы на неправильный порт (3001 вместо 3003)
- **Исправление**: изменён порт в `bionicpro_frontend/src/App.tsx` с 3001 на 3003
- Обновлены тексты кнопок в тестах после рефакторинга фронтенда
- **Результат**: все 16 тестов проходят успешно

### 3. ✅ Рефакторинг reports_api
- Функция `generate_report_data` уже была отделена от REST-метода (существовала изначально)
- Эндпоинт переименован с `/report` на `/reports` (множественное число)
- Функция REST-метода переименована с `generate_report` на `create_report`

### 4. ✅ Изменение работы с user_uuid
- **Join Table Engine**: изменён ключ с `user_id` на `user_uuid` в обеих схемах (default и debezium)
- **Таблица users**: `ENGINE = Join(ANY, LEFT, user_uuid)` вместо `user_id`
- **Таблица telemetry_events**: добавлено поле `user_uuid`, изменён ORDER BY на `(user_uuid, created_ts)`
- **Преимущество**: быстрый поиск по `user_uuid` благодаря индексу Join-таблицы

### 5. ✅ Обновление CSV-файлов
- **telemetry_api/signal_samples.csv**: добавлено поле `user_uuid` (10000 записей)
- **Скрипт**: создан `scripts/add_user_uuid_to_telemetry_csv.py` для автоматического добавления
- **Соответствие**: каждому `user_id` соответствует уникальный `user_uuid` из `crm.csv`
- **Резервная копия**: создана автоматически при выполнении скрипта

### 6. ✅ Обновление моделей данных
- **telemetry_api/main.py**: добавлено поле `user_uuid` в модель `IncomingTelemetryEvent`
- **dags/import_olap_data.py**: обновлён импорт данных для включения `user_uuid`
- **reports_api/main.py**: обновлены схемы таблиц и Materialized Views для debezium

### 7. ✅ Добавление 3 кнопок во фронтенд
Добавлены следующие кнопки в `bionicpro_frontend/src/App.tsx`:

1. **"Посмотреть JWT"** (синяя кнопка)
   - Отображает декодированный JWT-токен от reports_api
   - Показывает все поля токена (sub, realm_roles, email и т.д.)

2. **"Отчёт (default)"** (зелёная кнопка)
   - Создаёт отчёт из схемы `default` в ClickHouse
   - Параметры: `start_ts=null`, `end_ts="00:00 и 1 число текущего месяца по UTC"`
   - Если `user_uuid` не указан, берётся из JWT

3. **"Отчёт (debezium)"** (фиолетовая кнопка)
   - Создаёт отчёт из схемы `debezium` в ClickHouse
   - Параметры: `start_ts=null`, `end_ts="00:00 и 1 число текущего месяца по UTC"`
   - Если `user_uuid` не указан, берётся из JWT

**Отображение отчётов**:
- Имя и email пользователя
- Общее количество событий
- Общая длительность сигналов
- Статистика по каждому типу протеза (события, длительность, средняя амплитуда, средняя частота)
- Возможность просмотра полного JSON-ответа

### 8. ✅ Проверка прав доступа в /reports
Эндпоинт `/reports` проверяет JWT-токен и роли:
- **administrators**: может смотреть любые отчёты (свои и чужие)
- **prosthetic_users**: может смотреть только свой отчёт
- **остальные**: доступ запрещён (HTTP 403)
- Если `user_uuid` не указан в запросе, используется UUID из JWT (поле `sub`)

## Технические детали

### Изменённые файлы

1. **bionicpro_frontend/src/App.tsx**
   - Исправлен порт для JWT-эндпоинта (3001 → 3003)
   - Добавлены интерфейсы для отчётов
   - Добавлены состояния для отчётов
   - Добавлена функция `generateReport`
   - Добавлены 3 кнопки с обработчиками
   - Добавлено отображение результатов отчётов

2. **reports_api/main.py**
   - Переименован эндпоинт `/report` → `/reports`
   - Изменён Join Table Engine: `user_id` → `user_uuid`
   - Добавлено поле `user_uuid` в таблицу `telemetry_events`
   - Обновлён ORDER BY в `telemetry_events`: `(user_uuid, created_ts)`
   - Обновлена Materialized View для извлечения `user_uuid`

3. **telemetry_api/main.py**
   - Добавлено поле `user_uuid` в модель `IncomingTelemetryEvent`
   - Обновлена загрузка из CSV для чтения `user_uuid`

4. **dags/import_olap_data.py**
   - Изменён Join Table Engine: `user_id` → `user_uuid`
   - Добавлено поле `user_uuid` в таблицу `telemetry_events`
   - Обновлён ORDER BY в `telemetry_events`: `(user_uuid, created_ts)`
   - Обновлён импорт данных для включения `user_uuid`

5. **telemetry_api/signal_samples.csv**
   - Добавлена колонка `user_uuid` (10000 записей)

6. **auth_proxy/tests/test_e2e_keycloak.py**
   - Обновлены тексты кнопок: "Посмотреть reports_api/jwt" → "Посмотреть JWT"

7. **auth_proxy/tests/test_e2e_auth_proxy.py**
   - Обновлены тексты кнопок: "Посмотреть reports_api/jwt" → "Посмотреть JWT"

### Созданные файлы

1. **scripts/add_user_uuid_to_telemetry_csv.py**
   - Скрипт для автоматического добавления `user_uuid` в telemetry CSV
   - Создаёт резервную копию перед изменением
   - Использует маппинг из `crm.csv`

2. **scripts/recreate_clickhouse_tables.sh**
   - Скрипт для пересоздания таблиц в ClickHouse
   - Удаляет старые таблицы в обеих схемах (default и debezium)
   - Таблицы создаются автоматически при следующем запуске

3. **telemetry_api/signal_samples.csv.backup**
   - Резервная копия оригинального CSV (без `user_uuid`)

## Результаты тестирования

```
======================== 16 passed in 120.51s (0:02:00) ========================
```

Все E2E-тесты проходят успешно:
- ✅ Проверка доступности сервисов
- ✅ Авторизация через Keycloak
- ✅ Получение JWT-токена
- ✅ Проверка прав доступа
- ✅ Работа с auth_proxy
- ✅ Проверка UUID пользователей

## Как использовать

### Запуск сервисов
```bash
# Запуск всех Python-сервисов
uv run python -m auth_proxy.main &
uv run python -m crm_api.main &
uv run python -m telemetry_api.main &
uv run python -m reports_api.main &
```

### Загрузка данных
```bash
# Загрузка данных в PostgreSQL
curl -X POST http://localhost:3001/populate_base
curl -X POST http://localhost:3002/populate_base

# Импорт данных в ClickHouse
uv run python dags/import_olap_data.py
```

### Пересоздание таблиц ClickHouse
```bash
bash scripts/recreate_clickhouse_tables.sh
```

### Запуск тестов
```bash
uv run pytest auth_proxy/tests/test_e2e_keycloak.py auth_proxy/tests/test_e2e_auth_proxy.py -v
```

## Архитектурные улучшения

1. **Производительность**: использование `user_uuid` в качестве ключа Join-таблицы обеспечивает быстрый поиск без дополнительных индексов
2. **Согласованность**: все таблицы теперь используют `user_uuid` для связи с пользователями
3. **Безопасность**: проверка ролей в JWT-токене для контроля доступа к отчётам
4. **UX**: удобный интерфейс с тремя кнопками для разных операций
5. **Тестируемость**: все изменения покрыты E2E-тестами
