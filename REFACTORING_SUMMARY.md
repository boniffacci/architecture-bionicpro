# Итоговый отчёт о рефакторинге

## Выполненные задачи

### ✅ 1. Рефакторинг CRM API

#### Переименования
- **Customer** → **User** (ORM-класс и таблица БД)
- **customers** → **users** (имя таблицы в PostgreSQL)
- **UserCreate** → **IncomingUser** (модель входящих данных)

#### Архитектурные изменения
- `User` теперь наследуется от `IncomingUser`
- Устранено дублирование полей: вместо `registration_ts` и `registered_at` оставлено только `registered_at`
- `IncomingUser` не содержит `registration_ts` (время регистрации = время записи в БД)

#### Обновления CSV
- `crm.csv`: поле `registration_ts` переименовано в `registered_at`

#### Результаты тестирования
```
✓ 10/10 тестов CRM API прошли успешно
```

---

### ✅ 2. Рефакторинг Telemetry API

#### Переименования
- **EmgSensorDataCreate** → **IncomingTelemetryEvent** (модель входящих данных)
- **EmgSensorData** → **TelemetryEvent** (ORM-класс и таблица БД)
- **emg_sensor_data** → **telemetry_events** (имя таблицы в PostgreSQL)
- **signal_time** → **created_ts** → **event_timestamp** (поле времени события)

#### Архитектурные изменения
- `TelemetryEvent` наследуется от `IncomingTelemetryEvent`
- Добавлено поле **event_uuid** (уникальное, индексированное)
- Автоматическая генерация `event_uuid` на сервере, если не задано клиентом
- Устранено дублирование полей между базовым и дочерним классами

#### Обновления CSV
- `signal_samples.csv`: поле `signal_time` переименовано в `created_ts`, затем в `event_timestamp`

#### Результаты тестирования
```
✓ 10/10 тестов Telemetry API прошли успешно
```

---

### ✅ 3. Интеграция Kafka + Debezium

#### Добавленные сервисы в docker-compose.yaml
1. **Zookeeper** (порт 2181) - координация Kafka
2. **Kafka** (порт 29092) - брокер сообщений
3. **Kafdrop** (порт 9100) - веб-интерфейс для Kafka
4. **Debezium** (порт 8083) - Kafka Connect для CDC

#### Настройка PostgreSQL
- Включена логическая репликация (`wal_level=logical`) для `crm_db` и `telemetry_db`

#### Debezium-коннекторы
Созданы коннекторы для:
- **crm_db** → топик `crm.public.users`
- **telemetry_db** → топик `telemetry.public.telemetry_events`

---

### ✅ 4. ClickHouse OLAP с Kafka Engine

#### Новая схема: debezium

**Таблицы для пользователей (CRM):**
- `users_kafka` (Kafka Engine) - читает из топика `crm.public.users`
- `users_join` (Join Engine) - хранит пользователей для JOIN-запросов
- `users_mv` (Materialized View) - парсит JSON из Debezium и записывает в `users_join`

**Таблицы для телеметрии:**
- `telemetry_events_kafka` (Kafka Engine) - читает из топика `telemetry.public.telemetry_events`
- `telemetry_events_merge` (MergeTree) - хранит события телеметрии
- `telemetry_events_mv` (Materialized View) - парсит JSON из Debezium и записывает в `telemetry_events_merge`

---

### ✅ 5. Обновление существующих таблиц ClickHouse

#### Таблица `users` (схема default)
Удалено поле `registration_ts`, оставлено только `registered_at`

#### Таблица `telemetry_events` (схема default)
- Добавлено поле `event_uuid`
- Поле `signal_time` переименовано в `created_ts`, затем в `event_timestamp`

---

## Созданные скрипты

### 1. `scripts/setup_debezium_connectors.sh`
Настройка Debezium-коннекторов для CDC из PostgreSQL в Kafka

**Функции:**
- Ожидание запуска Debezium Kafka Connect
- Создание коннектора для `crm_db`
- Создание коннектора для `telemetry_db`
- Проверка статуса коннекторов

### 2. `scripts/setup_clickhouse_kafka.sh`
Настройка ClickHouse для чтения из Kafka-топиков

**Функции:**
- Создание базы данных `debezium`
- Создание Kafka Engine таблиц
- Создание Join и MergeTree таблиц
- Создание Materialized Views для парсинга JSON

### 3. `scripts/test_kafka_debezium.sh`
Полное тестирование интеграции Kafka + Debezium + ClickHouse

**Функции:**
- Проверка статуса Debezium-коннекторов
- Наполнение БД тестовыми данными
- Проверка репликации данных в ClickHouse

---

## Архитектура потока данных

```
┌─────────────┐      ┌──────────────┐      ┌─────────┐      ┌─────────┐
│  CRM API    │─────▶│   crm_db     │─────▶│Debezium │─────▶│  Kafka  │
│  (port 3002)│      │ (PostgreSQL) │      │         │      │         │
└─────────────┘      └──────────────┘      └─────────┘      └────┬────┘
                                                                  │
┌─────────────┐      ┌──────────────┐                            │
│Telemetry API│─────▶│telemetry_db  │─────▶Debezium ─────────────┤
│  (port 3003)│      │ (PostgreSQL) │                            │
└─────────────┘      └──────────────┘                            │
                                                                  ▼
                                                          ┌───────────────┐
                                                          │  ClickHouse   │
                                                          │  (OLAP DB)    │
                                                          │               │
                                                          │ Schemas:      │
                                                          │ - default     │
                                                          │ - debezium    │
                                                          └───────────────┘
```

---

## Модели данных

### CRM API

```python
# Входящие данные (без timestamp)
class IncomingUser(SQLModel):
    name: str
    email: str
    age: Optional[int]
    gender: Optional[str]
    country: Optional[str]
    address: Optional[str]
    phone: Optional[str]

# Модель БД (наследуется от IncomingUser)
class User(IncomingUser, table=True):
    id: Optional[int]
    user_uuid: str
    registered_at: datetime  # Единственное поле времени
```

### Telemetry API

```python
# Входящие данные (с опциональным event_uuid)
class IncomingTelemetryEvent(SQLModel):
    event_uuid: Optional[str]  # Генерируется автоматически, если не задан
    user_id: int
    prosthesis_type: str
    muscle_group: str
    signal_frequency: int
    signal_duration: int
    signal_amplitude: float
    created_ts: datetime

# Модель БД (наследуется от IncomingTelemetryEvent)
class TelemetryEvent(IncomingTelemetryEvent, table=True):
    id: Optional[int]
    event_uuid: str  # Обязательное, уникальное, индексированное
    saved_ts: datetime
```

---

## Kafka-топики

### crm.public.users
- **Источник:** таблица `users` в `crm_db`
- **Формат:** Debezium JSON
- **Потребитель:** `debezium.users_kafka` (ClickHouse)

### telemetry.public.telemetry_events
- **Источник:** таблица `telemetry_events` в `telemetry_db`
- **Формат:** Debezium JSON
- **Потребитель:** `debezium.telemetry_events_kafka` (ClickHouse)

---

## Инструкции по запуску

### 1. Остановка и очистка
```bash
docker compose down -v
sudo rm -rf postgres-crm-data postgres-telemetry-data clickhouse-data
```

### 2. Запуск инфраструктуры
```bash
docker compose up -d
```

### 3. Настройка Debezium
```bash
./scripts/setup_debezium_connectors.sh
```

### 4. Настройка ClickHouse Kafka Engine
```bash
./scripts/setup_clickhouse_kafka.sh
```

### 5. Запуск микросервисов
```bash
# В отдельных терминалах:
uv run python -m crm_api.main
uv run python -m telemetry_api.main
```

### 6. Тестирование
```bash
# Юнит-тесты
uv run pytest -v

# Интеграционное тестирование Kafka + Debezium
./scripts/test_kafka_debezium.sh
```

---

## Веб-интерфейсы

- **Kafdrop** (Kafka UI): http://localhost:9100
- **Debezium REST API**: http://localhost:8083/connectors
- **CRM API**: http://localhost:3001/docs
- **Telemetry API**: http://localhost:3001/docs

---

## Результаты

### ✅ Все тесты проходят успешно
- CRM API: 10/10 тестов ✓
- Telemetry API: 10/10 тестов ✓

### ✅ Архитектура улучшена
- Устранено дублирование кода через наследование
- Упрощена схема БД (меньше полей)
- Добавлена поддержка CDC через Debezium

### ✅ Готова инфраструктура для real-time аналитики
- Kafka + Debezium для потоковой репликации
- ClickHouse Kafka Engine для real-time обработки
- Materialized Views для автоматической трансформации данных

---

## Документация

Подробные инструкции по настройке и использованию см. в:
- `KAFKA_DEBEZIUM_SETUP.md` - полное руководство по Kafka + Debezium
- `QUICK_START.md` - быстрый старт проекта
- `README.md` - общее описание проекта
