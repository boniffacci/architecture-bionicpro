# BionicPRO: АРХИТЕКТУРА ДАННЫХ И ETL-ПРОЦЕСС
# Полное описание для 9-го спринта курса "Архитектура ПО"

## СОДЕРЖАНИЕ
1. Обзор решения
2. Схема данных
3. Описание витрин отчётов
4. ETL-процесс
5. Ключевые показатели (KPI)
6. Инструкции по запуску

---

## 1. ОБЗОР РЕШЕНИЯ

### Контекст задачи

В ходе 9-го спринта требуется разработать сервис отчётов для BionicPRO. Пользователи хотят получать данные о работе своих протезов в виде отчёта, что требует:

1. **Создания OLTP-баз** (PostgreSQL):
   - **crm_db** — информация о пользователях, протезах, подписках, платежах
   - **telemetry_db** — события и метрики с протезов в реальном времени

2. **Создания OLAP-базы** (ClickHouse):
   - **reports_db** — витрины данных для быстрого доступа к отчётам

3. **Разработки ETL-процесса** (Apache Airflow):
   - Ежедневное заполнение витрин на основе данных из OLTP-баз
   - Преобразование операционных данных в аналитические форматы

### Почему ClickHouse?

ClickHouse выбран потому, что:
- **OLAP-ориентирован** — оптимизирован для аналитических запросов (большие объёмы данных, много строк, мало столбцов)
- **Сжатие данных** — встроенное сжатие уменьшает требования к памяти
- **Партиционирование** — позволяет быстро фильтровать данные по датам
- **Быстрые GROUP BY** — перфект для агрегаций и витрин
- **ORDER BY оптимизация** — первичный ключ с ORDER BY позволяет быстро искать по пользователям

### Архитектура данных

```
┌─────────────────────────────────────────────────────────────────┐
│                      ИСХОДНЫЕ СИСТЕМЫ (OLTP)                     │
├──────────────────────────────┬──────────────────────────────────┤
│                              │                                   │
│  CRM-система (PostgreSQL)    │  Телеметрия (PostgreSQL)         │
│  crm_db                      │  telemetry_db                    │
│                              │                                   │
│ ├── crm_users                │ ├── telemetry_events             │
│ ├── crm_prosthetics          │ └── battery_metrics              │
│ ├── crm_subscriptions        │                                   │
│ ├── crm_payments             │                                   │
│ └── crm_support_tickets      │                                   │
└──────────────────────────────┴──────────────────────────────────┘
                     ↓              ↓
            ┌────────────────────────────────┐
            │   AIRFLOW ETL DAG (DAG ID:     │
            │   bionicpro_etl_daily)         │
            │                                │
            │ ├── Extract CRM & Telemetry   │
            │ ├── Transform metrics         │
            │ └── Load to ClickHouse        │
            │                                │
            │ Расписание: ежедневно 02:00   │
            └────────────────────────────────┘
                     ↓
        ┌──────────────────────────────┐
        │  АНАЛИТИЧЕСКИЕ ВИТРИНЫ       │
        │  (ClickHouse - reports_db)    │
        │                              │
        │ ├── report_user_monthly_metrics    │
        │ └── report_prosthetic_monthly_metrics │
        │                              │
        │ Партиции по месяцам          │
        │ ORDER BY (user_id, date)     │
        └──────────────────────────────┘
                     ↓
        ┌──────────────────────────────┐
        │  API ОТЧЁТОВ                  │
        │  /reports/{user_id}           │
        │                              │
        │ Быстрые запросы по user_id   │
        │ Кеширование в S3 + CDN       │
        └──────────────────────────────┘
```

---

## 2. СХЕМА ДАННЫХ

### 2.1 CRM БД (PostgreSQL - crm_db)

#### Таблица: crm_users
```
Пользователи системы BionicPRO

Столбцы:
  user_id             INTEGER PRIMARY KEY   -- Уникальный идентификатор
  user_uuid           VARCHAR(36) UNIQUE    -- UUID v4 для интеграции
  first_name          VARCHAR(100)          -- Имя
  last_name           VARCHAR(100)          -- Фамилия
  email               VARCHAR(255) UNIQUE   -- Электронная почта
  phone               VARCHAR(20)           -- Телефон
  created_at          TIMESTAMP             -- Дата создания
  updated_at          TIMESTAMP             -- Дата обновления

Примеры данных:
  (1, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Александр', 'Иванов',
   'alex.ivanov@bionicpro.ru', '+79999999999', ...)
```

#### Таблица: crm_prosthetics
```
Протезы, принадлежащие пользователям

Столбцы:
  prosthetic_id       INTEGER PRIMARY KEY
  user_id             INTEGER FK → crm_users
  prosthetic_uuid     VARCHAR(36) UNIQUE    -- Идентификатор для API
  device_type         VARCHAR(50)           -- left_arm | right_arm | left_leg | right_leg
  serial_number       VARCHAR(50) UNIQUE    -- Серийный номер
  model               VARCHAR(100)          -- Модель (BionicPRO X1, X2, X3 Pro)
  purchase_date       DATE                  -- Дата покупки
  warranty_end_date   DATE                  -- Конец гарантии
  is_active           BOOLEAN               -- Активен ли протез
  created_at          TIMESTAMP
  updated_at          TIMESTAMP

Примеры данных:
  (1, 1, 'p1234567-89ab-cdef-0123-456789abcdef', 'left_arm',
   'SN-123456', 'BionicPRO X2', '2023-01-15', '2024-01-15', true, ...)
```

#### Таблица: crm_subscriptions
```
Подписки на сопровождение протезов

Столбцы:
  subscription_id     INTEGER PRIMARY KEY
  user_id             INTEGER FK → crm_users
  subscription_type   VARCHAR(50)           -- basic | premium | enterprise
  start_date          DATE                  -- Начало подписки
  end_date            DATE NULL             -- Конец подписки (NULL если активна)
  is_active           BOOLEAN               -- Статус активности
  monthly_cost        NUMERIC(10,2)         -- Ежемесячная стоимость
  created_at          TIMESTAMP
  updated_at          TIMESTAMP

Примеры:
  basic     → 2999.00 руб/месяц
  premium   → 5999.00 руб/месяц
  enterprise → 9999.00 руб/месяц
```

#### Таблица: crm_payments
```
История платежей

Столбцы:
  payment_id          INTEGER PRIMARY KEY
  user_id             INTEGER FK → crm_users
  subscription_id     INTEGER FK → crm_subscriptions
  payment_date        TIMESTAMP             -- Дата/время платежа
  amount              NUMERIC(10,2)         -- Сумма платежа
  payment_method      VARCHAR(50)           -- card | bank_transfer | paypal
  status              VARCHAR(20)           -- success | failed | pending
  description         TEXT                  -- Описание платежа
  created_at          TIMESTAMP

Примеры:
  (101, 1, 5, '2024-01-15 10:30:00', 2999.00, 'card', 'success', ...)
  (102, 1, 5, '2024-02-15 10:30:00', 2999.00, 'card', 'failed', ...)
```

#### Таблица: crm_support_tickets
```
Обращения в техподдержку

Столбцы:
  ticket_id           INTEGER PRIMARY KEY
  user_id             INTEGER FK → crm_users
  prosthetic_id       INTEGER FK → crm_prosthetics (NULL возможен)
  title               VARCHAR(255)          -- Тема обращения
  description         TEXT                  -- Описание проблемы
  status              VARCHAR(20)           -- open | in_progress | resolved | closed
  created_at          TIMESTAMP
  updated_at          TIMESTAMP
  resolved_at         TIMESTAMP NULL        -- Время решения

Примеры:
  "Протез не включается"
  "Проблемы с батареей"
  "Дёргается движение"
```

### 2.2 TELEMETRY БД (PostgreSQL - telemetry_db)

#### Таблица: telemetry_events
```
События с протезов (events streaming)

Столбцы:
  event_id            INTEGER PRIMARY KEY
  prosthetic_id       INTEGER FK → crm_prosthetics (через крест-БД связь)
  event_type          VARCHAR(50)           -- power_on | power_off | error | 
                                            -- charging_started | calibration | etc.
  event_timestamp     TIMESTAMP             -- Время события на протезе
  event_value         VARCHAR(255)          -- Дополнительные данные (battery_80%, etc.)
  severity            VARCHAR(20)           -- info | warning | error | critical
  created_at          TIMESTAMP             -- Время получения сервером

Примеры:
  event_type='power_on'     severity='info'       event_value='battery_85%'
  event_type='error'        severity='error'      event_value='motor_fault'
  event_type='charging_started' severity='info'  event_value='100mA'
```

#### Таблица: battery_metrics
```
Метрики батареи (снимаются несколько раз в сутки)

Столбцы:
  metric_id           INTEGER PRIMARY KEY
  prosthetic_id       INTEGER FK
  metric_timestamp    TIMESTAMP             -- Время снятия метрики
  charge_level        FLOAT                 -- 0-100 (%)
  current_ma          FLOAT                 -- Ток в миллиамперах
                                            -- Положительный = зарядка
                                            -- Отрицательный = разрядка
  is_charging         BOOLEAN               -- Протез на зарядке?
  created_at          TIMESTAMP

Примеры:
  charge_level=95.5  current_ma=150.2  is_charging=true   (зарядка)
  charge_level=45.2  current_ma=-80.5  is_charging=false  (работа)
```

### 2.3 REPORTS БД (ClickHouse - reports_db)

#### Витрина 1: report_user_monthly_metrics
```
Ежемесячные финансовые метрики пользователя

Столбцы (Dimension columns):
  report_date         DATE                  -- Первый день месяца
  user_id             INT                   -- ID пользователя
  user_uuid           String                -- UUID пользователя

Столбцы (Metric columns):
  total_payments                DECIMAL     -- Все платежи (успешные + неудачные)
  successful_payments           DECIMAL     -- Только успешные платежи
  failed_payments_count         INT         -- Количество неудачных платежей
  active_subscriptions_count    INT         -- Активные подписки на момент
  subscription_cost_total       DECIMAL     -- Сумма всех подписок

Метаданные:
  last_updated        TIMESTAMP             -- Время последнего обновления
  created_at          TIMESTAMP             -- Время создания записи

ClickHouse Специфика:
  ENGINE = MergeTree()
  ORDER BY (user_id, report_date)           -- Сортировка по пользователю и дате
  PARTITION BY toYYYYMM(report_date)        -- Партиции по месяцам

Пример данных:
  report_date='2024-01-01' user_id=1 total_payments=8997.00
  successful_payments=5998.00 failed_payments_count=1
  active_subscriptions_count=1 subscription_cost_total=2999.00
```

#### Витрина 2: report_prosthetic_monthly_metrics
```
Ежемесячные технические метрики протеза

Столбцы (Dimension):
  report_date         DATE
  prosthetic_id       INT
  user_id             INT
  user_uuid           String
  prosthetic_uuid     String
  device_type         String                -- left_arm | right_arm | etc.

Столбцы (Metrics - Использование):
  power_on_count      INT                   -- Количество включений
  power_off_count     INT                   -- Количество выключений
  total_active_hours  FLOAT                 -- Часы активного использования

Столбцы (Metrics - Батарея):
  avg_discharge_rate_active    FLOAT        -- Средняя разрядка при работе (mAh/h)
  avg_discharge_rate_idle      FLOAT        -- Средняя разрядка в режиме ожидания
  avg_charge_rate              FLOAT        -- Средняя скорость зарядки (mAh/h)
  charge_cycles                INT          -- Количество циклов зарядки

Столбцы (Metrics - Надёжность):
  warning_count       INT                   -- Предупреждения
  error_count         INT                   -- Ошибки (восстанавливаемые)
  critical_error_count INT                  -- Критические сбои
  downtime_minutes    INT                   -- Минуты простоя

Метаданные:
  last_updated        TIMESTAMP
  created_at          TIMESTAMP

ClickHouse Специфика:
  ENGINE = MergeTree()
  ORDER BY (user_id, prosthetic_id, report_date)
  PARTITION BY toYYYYMM(report_date)

Пример данных:
  report_date='2024-01-01' prosthetic_id=1 user_id=1
  power_on_count=28 power_off_count=27 total_active_hours=12.5
  avg_discharge_rate_active=85.5 avg_charge_rate=200.0 charge_cycles=2
  error_count=0 critical_error_count=0 downtime_minutes=0
```

---

## 3. ОПИСАНИЕ ВИТРИН ОТЧЁТОВ

### Витрина 1: report_user_monthly_metrics

**Назначение**: Финансовый отчёт пользователя по месяцам

**Показатели (KPI)**:
- `total_payments` — Все платежи в месяц (успешные + неудачные)
- `successful_payments` — Только успешно прошедшие платежи
- `failed_payments_count` — Число неудачных попыток платежа
- `active_subscriptions_count` — Сколько подписок активно
- `subscription_cost_total` — Сумма всех активных подписок

**Пример отчёта пользователя на январь 2024**:
```
Период: январь 2024
Всего платежей: 8997.00 руб
Успешных: 5998.00 руб
Ошибок платежа: 1
Активные подписки: 1
Стоимость подписок: 2999.00 руб/месяц
```

**Зачем нужна**:
- Отслеживание доходов по месяцам
- Выявление проблем с платежами
- Анализ retention (удержание) пользователей

### Витрина 2: report_prosthetic_monthly_metrics

**Назначение**: Технический отчёт о состоянии протеза

**Показатели (KPI)**:

1. **Использование**:
   - `power_on_count` / `power_off_count` — Как часто включают/выключают протез
   - `total_active_hours` — Всего часов использования в месяц

2. **Батарея** (ключевой показатель качества):
   - `avg_discharge_rate_active` — Скорость разрядки при работе
   - `avg_discharge_rate_idle` — Скорость разрядки в режиме ожидания
   - `avg_charge_rate` — Скорость зарядки
   - `charge_cycles` — Количество полных циклов зарядки

3. **Надёжность**:
   - `warning_count` — Предупреждения (неломающие)
   - `error_count` — Ошибки (восстанавливаемые)
   - `critical_error_count` — Сбои (требующие перезагрузки)
   - `downtime_minutes` — Минуты, когда протез не работал

**Пример отчёта для протеза (январь 2024)**:
```
Протез: BionicPRO X2 (левая рука)
Использование: 28 включений, 27 выключений, 12.5 часов активной работы

Батарея:
  Разрядка при работе: 85.5 mAh/h
  Разрядка в покое: 25.7 mAh/h
  Зарядка: 200.0 mAh/h
  Циклов зарядки: 2 (норма для месяца)

Надёжность:
  Предупреждения: 0
  Ошибок: 0
  Критических сбоев: 0
  Простоев: 0 минут

Статус: ✓ ЗДОРОВ
```

**Преимущества для ClickHouse**:

1. **Партиционирование по месяцам** (`PARTITION BY toYYYYMM(report_date)`):
   - Быстрое удаление старых данных (старше 3 лет → DROP PARTITION)
   - Параллельное сканирование нескольких месяцев

2. **ORDER BY (user_id, prosthetic_id, report_date)**:
   - Поиск всех протезов пользователя: O(log N) вместо O(N)
   - Эффективное чтение: диски не нужно крутить туда-сюда
   - Отлично работает с WHERE user_id = ? AND prosthetic_id = ?

3. **Сжатие**:
   - Данные за год при 15 пользователях ~100 KB (вместо 10 MB в JSON)

---

## 4. ETL-ПРОЦЕСС

### 4.1 Архитектура ETL

```
DAG: bionicpro_etl_daily
Запуск: ежедневно в 02:00 UTC (после бизнес-часов)

┌─────────────────────────────────────────────────────────────┐
│                    EXTRACT LAYER (параллель)                │
├──────────────────────────────┬──────────────────────────────┤
│ extract_crm_data             │ extract_telemetry_data       │
│                              │                              │
│ - Берём платежи за вчера     │ - Берём события за вчера     │
│ - Берём активные подписки    │ - Берём метрики батареи     │
│ - Пишем в XCom              │ - Пишем в XCom              │
└──────────────────────────────┴──────────────────────────────┘
                 ↓                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    TRANSFORM LAYER (параллель)               │
├──────────────────────────────┬──────────────────────────────┤
│ transform_user_metrics       │ transform_prosthetic_metrics │
│                              │                              │
│ - Агрегируем платежи         │ - Агрегируем события         │
│ - Считаем KPI                │ - Считаем метрики батареи   │
│ - Подготавливаем для CH      │ - Подготавливаем для CH      │
└──────────────────────────────┴──────────────────────────────┘
                 ↓                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    LOAD LAYER                                │
├─────────────────────────────────────────────────────────────┤
│ load_to_clickhouse                                           │
│                                                              │
│ - INSERT INTO report_user_monthly_metrics                   │
│ - INSERT INTO report_prosthetic_monthly_metrics             │
│ - Обновляет витрины для отчётов                            │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Поток данных

**Пример: Платёж пользователя**

```
1. Пользователь оплачивает подписку в CRM (10:30 утра)
   INSERT INTO crm_payments (user_id=1, amount=2999.00, status='success')

2. Ночью в 02:00 (через 15.5 часов) запускается DAG:
   
   EXTRACT:
     SELECT SUM(amount) WHERE user_id=1 AND DATE(payment_date)=yesterday
     Результат: total_payments = 2999.00
   
   TRANSFORM:
     total_payments = 2999.00
     successful_payments = 2999.00
     failed_payments_count = 0
   
   LOAD:
     INSERT INTO report_user_monthly_metrics (
       report_date='2024-01-01',
       user_id=1,
       total_payments=2999.00,
       successful_payments=2999.00,
       ...
     )

3. Утром пользователь смотрит отчёт:
   GET /reports/user/1?month=2024-01
   → быстро читает уже посчитанные витрины из ClickHouse
```

### 4.3 SQL-запросы в ETL

#### Extract CRM: Платежи и подписки
```sql
-- Берём все платежи за вчерашний день по каждому пользователю
SELECT 
    u.user_id,
    u.user_uuid,
    SUM(CASE WHEN pay.status = 'success' THEN pay.amount ELSE 0 END) as successful_payments,
    SUM(CASE WHEN pay.status = 'failed' THEN pay.amount ELSE 0 END) as failed_payments,
    COUNT(CASE WHEN pay.status = 'failed' THEN 1 END) as failed_count,
    COUNT(DISTINCT s.subscription_id) as active_subs,
    SUM(s.monthly_cost) as subscription_cost
FROM crm_users u
LEFT JOIN crm_subscriptions s ON u.user_id = s.user_id AND s.is_active = true
LEFT JOIN crm_payments pay ON s.subscription_id = pay.subscription_id 
  AND DATE(pay.payment_date) = DATE(CURRENT_DATE - INTERVAL '1 day')
GROUP BY u.user_id, u.user_uuid
```

#### Extract Telemetry: События
```sql
-- Агрегируем события для каждого протеза
SELECT 
    te.prosthetic_id,
    COUNT(CASE WHEN te.event_type = 'power_on' THEN 1 END) as power_on_count,
    COUNT(CASE WHEN te.severity = 'warning' THEN 1 END) as warning_count,
    COUNT(CASE WHEN te.severity = 'error' THEN 1 END) as error_count,
    COUNT(CASE WHEN te.severity = 'critical' THEN 1 END) as critical_count
FROM telemetry_events te
WHERE DATE(te.event_timestamp) = DATE(CURRENT_DATE - INTERVAL '1 day')
GROUP BY te.prosthetic_id
```

#### Transform: Меtrики батареи
```sql
-- Рассчитываем метрики батареи за день
SELECT 
    prosthetic_id,
    AVG(CASE WHEN current_ma < 0 THEN ABS(current_ma) ELSE NULL END) as avg_discharge_active,
    AVG(CASE WHEN is_charging THEN current_ma ELSE NULL END) as avg_charge_rate,
    COUNT(DISTINCT 
        CASE WHEN charge_level > 95 AND LAG(charge_level) OVER (...) < 50
        THEN DATE(metric_timestamp) END
    ) as charge_cycles
FROM battery_metrics
WHERE DATE(metric_timestamp) = DATE(CURRENT_DATE - INTERVAL '1 day')
GROUP BY prosthetic_id
```

### 4.4 Расписание и SLA

```
Расписание:  Ежедневно в 02:00 UTC
Окно:        00:00 - 05:00 UTC (буфер на случай задержек)
Timeout:     30 минут (если дольше — алерт)
Retries:     1 попытка через 5 минут
SLA:         Данные должны быть готовы к 06:00 UTC
```

---

## 5. КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ (KPI) ДЛЯ ОТЧЁТОВ

### 5.1 Финансовые KPI (витрина 1)

| KPI | Формула | Пример | Для кого |
|-----|---------|--------|----------|
| **Месячный доход на пользователя** | SUM(successful_payments) | 2999.00 руб | Финансы |
| **Коэффициент успешности платежей** | successful_payments / total_payments | 95% | Финансы |
| **Среднее число подписок на пользователя** | COUNT(active_subscriptions) | 1.2 | Продажи |
| **ARR (Annual Recurring Revenue)** | subscription_cost_total × 12 | 35988 руб/год | CEO |

### 5.2 Технические KPI (витрина 2)

| KPI | Формула | Пример | Для кого |
|-----|---------|--------|----------|
| **Дневное использование** | AVG(power_on_count) / 30 | 0.9 часов/день | Пользователь |
| **Здоровье батареи** | IF(charge_cycles < 3) GOOD | 2 цикла/месяц | ML-команда |
| **Надёжность** | 100 - (error_count + critical_error_count)/power_on_count × 100 | 99.8% | Инженеры |
| **Среднее время до перезарядки** | 24h / charge_cycles | 12 часов | Пользователь |

### 5.3 Интеграция с API отчётов

```python
# API endpoint для получения отчёта
GET /reports/user/{user_id}?month=2024-01

Ответ:
{
  "period": "2024-01",
  "user_id": 1,
  "financial": {
    "total_payments": "8997.00",
    "successful_payments": "5998.00",
    "failed_payments_count": 1,
    "active_subscriptions": 1,
    "monthly_cost": "2999.00"
  },
  "devices": [
    {
      "prosthetic_id": 1,
      "device_type": "left_arm",
      "usage_hours": 12.5,
      "power_on_count": 28,
      "battery_health": "good",
      "downtime_minutes": 0,
      "errors": 0
    }
  ],
  "status": "healthy"
}
```

---

## 6. ИНСТРУКЦИИ ПО ЗАПУСКУ

### 6.1 Предварительные требования

```bash
# Установленное ПО:
- Docker & Docker Compose
- Python 3.9+
- PostgreSQL (2 инстанса или 2 БД)
- ClickHouse (server + client)
- Apache Airflow 2.5+
```

### 6.2 Инициализация БД

```bash
# 1. Создаём БД
psql -U postgres -c "CREATE DATABASE crm_db;"
psql -U postgres -c "CREATE DATABASE telemetry_db;"

# 2. Генерируем схему (SQLAlchemy создаст таблицы)
python -m database_schemas

# 3. Заполняем тестовыми данными
python generate_test_data.py

# 4. Проверяем данные
psql -U postgres -d crm_db -c "SELECT COUNT(*) FROM crm_users;"
# Output: 12 пользователей ✓

psql -U postgres -d telemetry_db -c "SELECT COUNT(*) FROM telemetry_events;"
# Output: ~450000 событий ✓
```

### 6.3 Настройка ClickHouse

```sql
-- Подключаемся к ClickHouse
clickhouse-client

-- Создаём БД
CREATE DATABASE reports_db;

-- Создаём витрину 1
CREATE TABLE reports_db.report_user_monthly_metrics (
    report_date Date,
    user_id Int32,
    user_uuid String,
    total_payments Decimal(10, 2),
    successful_payments Decimal(10, 2),
    failed_payments_count Int32,
    active_subscriptions_count Int32,
    subscription_cost_total Decimal(10, 2),
    last_updated DateTime,
    created_at DateTime
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (user_id, report_date);

-- Создаём витрину 2
CREATE TABLE reports_db.report_prosthetic_monthly_metrics (
    report_date Date,
    prosthetic_id Int32,
    user_id Int32,
    user_uuid String,
    prosthetic_uuid String,
    device_type String,
    power_on_count Int32,
    power_off_count Int32,
    total_active_hours Float32,
    avg_discharge_rate_active Float32,
    avg_discharge_rate_idle Float32,
    avg_charge_rate Float32,
    charge_cycles Int32,
    warning_count Int32,
    error_count Int32,
    critical_error_count Int32,
    downtime_minutes Int32,
    last_updated DateTime,
    created_at DateTime
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (user_id, prosthetic_id, report_date);
```

### 6.4 Развёртывание Airflow

```bash
# 1. Инициализируем Airflow
airflow db init

# 2. Устанавливаем переменные окружения
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="postgresql+psycopg2://airflow:airflow@localhost/airflow"
export AIRFLOW__CORE__DAGS_FOLDER="/path/to/dags"

# 3. Копируем DAG
cp airflow_etl_dag.py $AIRFLOW_HOME/dags/

# 4. Устанавливаем Variable'ы в Airflow UI или CLI:
airflow variables set CRM_DATABASE_URL "postgresql://postgres:password@localhost/crm_db"
airflow variables set TELEMETRY_DATABASE_URL "postgresql://postgres:password@localhost/telemetry_db"
airflow variables set CLICKHOUSE_DATABASE_URL "clickhouse://default:@localhost/reports_db"

# 5. Запускаем Scheduler и Webserver
airflow scheduler &
airflow webserver --port 8080 &

# DAG будет доступен по адресу http://localhost:8080
# Проверяем статус: DAG должен быть в списке и автоматически
# начнёт запускаться согласно расписанию
```

### 6.5 Проверка ETL

```bash
# Проверяем запуск DAG
airflow dags trigger -e 2024-01-02 bionicpro_etl_daily

# Смотрим логи
airflow tasks logs bionicpro_etl_daily extract_crm_data 2024-01-02

# Проверяем результаты в ClickHouse
clickhouse-client -d reports_db -q \
  "SELECT report_date, COUNT(*) FROM report_user_monthly_metrics GROUP BY report_date;"

# Должны вывести:
# 2024-01-01  12
# (12 пользователей за январь)
```

### 6.6 Тестирование отчётов

```bash
# Считаем с ClickHouse отчёт для пользователя 1 за январь
clickhouse-client -d reports_db -q \
  "SELECT * FROM report_user_monthly_metrics 
   WHERE user_id = 1 AND report_date = '2024-01-01'
   FORMAT JSON"

# Результат:
{
  "data": [{
    "report_date": "2024-01-01",
    "user_id": 1,
    "user_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "total_payments": "8997.00",
    "successful_payments": "5998.00",
    "failed_payments_count": 1,
    "active_subscriptions_count": 1,
    "subscription_cost_total": "2999.00"
  }]
}
```

---

## 7. ОПТИМИЗАЦИЯ И ЛУЧШИЕ ПРАКТИКИ

### 7.1 ClickHouse: Почему быстрый?

```
Запрос: "Дай мне все метрики для пользователя 1"

SELECT * FROM report_user_monthly_metrics WHERE user_id = 1;

OLTP (PostgreSQL):
  - Ищет в куче случайных местах на диске
  - 100 мс для 1 млн записей

OLAP (ClickHouse):
  - Данные заранее отсортированы по user_id (ORDER BY)
  - Бинарный поиск находит диапазон
  - Читает только нужные блоки
  - 1 мс для 100 млн записей (в 100 раз быстрее!)
```

### 7.2 Партиционирование: Зачем нужно?

```
Витрина за 3 года = 36 месячных партиций

Если удалить данные за 2021 год:
  OLTP БД: DELETE WHERE report_date < '2022-01-01'
           → Медленно, нужно перемещать данные
  
  ClickHouse: ALTER TABLE DROP PARTITION 202112
              → Мгновенно, просто удаляет файл

Если фильтровать по месяцу:
  WHERE report_date >= '2024-01-01' AND report_date < '2024-02-01'
  → ClickHouse скачивает только 1 партицию
  → В 36 раз меньше данных!
```

### 7.3 Масштабирование ETL

```
Текущее (учебный проект):
  - 12 пользователей
  - ~15 протезов
  - Запуск за 30 секунд

Реальное (BionicPRO в будущем):
  - 10,000 пользователей
  - ~15,000 протезов
  - Запуск за 1-2 минуты

Что делать для масштабирования?
  1. Добавить incremental вместо full refresh
     (загружать только новые/изменённые данные)
  2. Использовать Debezium + Kafka (вместо Airflow)
     (реал-тайм CDC: задание 4 спринта)
  3. Партиции по hour, а не по месяцам
     (если нужны почасовые отчёты)
  4. Использовать ReplicatedMergeTree
     (для надёжности и репликации данных)
```

### 7.4 Безопасность данных

```
Витрина содержит медицинские данные → GDPR/HIPAA compliance:

1. Шифрование на лету (PostgreSQL SSL/TLS)
2. Шифрование в ClickHouse (включить в конфиге)
3. Row-level security: пользователь видит только свои данные
   (проверка в API слое, не в БД)
4. Логирование доступа (audit trail)
5. Резервные копии (ежедневно, off-site)
```

---

## ЗАКЛЮЧЕНИЕ

Предложенная архитектура демонстрирует:

✓ **Разделение OLTP и OLAP** — CRM/Telemetry для операций, Reports для аналитики
✓ **ETL-процесс** — ежедневное преобразование операционных данных
✓ **Оптимизация для ClickHouse** — партиции по месяцам, ORDER BY по user_id
✓ **Масштабируемость** — простые добавления новых витрин
✓ **Безопасность** — разделение баз, контроль доступа

Для реального использования нужно добавить:
- Apache Airflow с KubernetesExecutor (как в вашей системе)
- Debezium + Kafka для CDC (задание 4)
- Redis кеширование для API отчётов
- Nginx reverse proxy + CDN (задание 3)
- Мониторинг DAG (Prometheus + Grafana)
