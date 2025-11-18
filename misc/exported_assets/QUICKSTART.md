# QUICKSTART.md
# Пошаговые инструкции для быстрого запуска

## Этап 1: Подготовка окружения (5 минут)

### 1.1 Установка зависимостей

```bash
# Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установите пакеты
pip install --upgrade pip
pip install sqlalchemy psycopg2-binary apache-airflow clickhouse-driver python-dateutil
```

### 1.2 Проверка PostgreSQL

```bash
# Убедитесь, что PostgreSQL запущен
psql --version

# Подключитесь к PostgreSQL
psql -U postgres

# В psql:
CREATE DATABASE crm_db;
CREATE DATABASE telemetry_db;
\q
```

## Этап 2: Создание схемы данных (2 минуты)

### 2.1 Используйте исправленный файл

```bash
# Используйте database_schemas_fixed.py вместо database_schemas.py

python database_schemas_fixed.py
```

**Ожидаемый вывод:**
```
Creating CRM database schema...
✓ CRM schema created
Creating Telemetry database schema...
✓ Telemetry schema created

All schemas created successfully!
```

### 2.2 Проверка таблиц

```bash
psql -d crm_db -c "\dt"
# Должны видеть: crm_users, crm_prosthetics, crm_subscriptions, crm_payments, crm_support_tickets

psql -d telemetry_db -c "\dt"
# Должны видеть: telemetry_events, battery_metrics
```

## Этап 3: Генерация тестовых данных (30 секунд)

### 3.1 Запуск генератора

**ВАЖНО**: Отредактируйте `generate_test_data.py` перед запуском:

Найдите в файле строку:
```python
if __name__ == "__main__":
    # Конфигурация БД
    CRM_DATABASE_URL = "postgresql://postgres:password@localhost:5432/crm_db"
    TELEMETRY_DATABASE_URL = "postgresql://postgres:password@localhost:5432/telemetry_db"
```

Замените `password` на реальный пароль PostgreSQL.

Затем запустите:
```bash
python generate_test_data.py
```

**Ожидаемый вывод:**
```
======================================================================
Генератор тестовых данных BionicPRO
======================================================================
Генерирую пользователей CRM...
✓ Создано 12 пользователей
Генерирую протезы CRM...
✓ Создано 15 протезов
Генерирую подписки CRM...
✓ Создано 9 подписок
Генерирую платежи CRM...
✓ Создано 234 платежей
Генерирую обращения в поддержку CRM...
✓ Создано 47 обращений в поддержку
Генерирую события телеметрии...
✓ Создано 456000 событий телеметрии
Генерирую метрики батареи...
✓ Создано 45000 метрик батареи
======================================================================
✓ ВСЕ ДАННЫЕ СГЕНЕРИРОВАНЫ УСПЕШНО!
======================================================================
```

### 3.2 Проверка данных

```bash
psql -d crm_db -c "SELECT COUNT(*) FROM crm_users;"
# Результат: 12

psql -d telemetry_db -c "SELECT COUNT(*) FROM telemetry_events;"
# Результат: 456000
```

## Этап 4: Настройка ClickHouse (5 минут)

### 4.1 Запуск ClickHouse в Docker

```bash
# Самый простой способ — использовать Docker
docker run -d \
  --name clickhouse \
  -p 8123:8123 \
  -p 9000:9000 \
  -v $(pwd)/clickhouse_data:/var/lib/clickhouse \
  clickhouse/clickhouse-server:latest
```

### 4.2 Создание витрин в ClickHouse

```bash
# Подключиться к ClickHouse
clickhouse-client

# Выполнить SQL:
```

Скопируйте и выполните в `clickhouse-client`:

```sql
-- Создаём БД
CREATE DATABASE reports_db;

-- Витрина 1: Финансовые метрики пользователей
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

-- Витрина 2: Технические метрики протезов
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

### 4.3 Проверка ClickHouse

```bash
clickhouse-client -q "SELECT COUNT(*) FROM reports_db.report_user_monthly_metrics;"
# Результат: 0 (это нормально, данные загрузятся через Airflow)

clickhouse-client -q "SHOW TABLES FROM reports_db;"
# Результат: report_prosthetic_monthly_metrics, report_user_monthly_metrics
```

## Этап 5: Настройка Apache Airflow (10 минут)

### 5.1 Инициализация Airflow

```bash
# Инициализируем Airflow БД
airflow db init

# Создаём админ-пользователя
airflow users create \
  --username admin \
  --password admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com
```

### 5.2 Установка переменных Airflow

```bash
# Метод 1: Через CLI (рекомендуется)
airflow variables set CRM_DATABASE_URL "postgresql://postgres:PASSWORD@localhost/crm_db"
airflow variables set TELEMETRY_DATABASE_URL "postgresql://postgres:PASSWORD@localhost/telemetry_db"
airflow variables set CLICKHOUSE_DATABASE_URL "clickhouse://default:@localhost/reports_db"

# Проверка:
airflow variables list | grep DATABASE
```

**Замените PASSWORD на реальный пароль PostgreSQL!**

### 5.3 Добавление DAG

```bash
# Найдите AIRFLOW_HOME
echo $AIRFLOW_HOME

# По умолчанию это ~/airflow
# Создайте папку dags, если её нет
mkdir -p ~/airflow/dags

# Скопируйте DAG
cp airflow_etl_dag.py ~/airflow/dags/
```

### 5.4 Запуск Airflow

```bash
# В одном терминале: Scheduler
airflow scheduler

# В другом терминале: Webserver
airflow webserver --port 8080
```

### 5.5 Проверка Airflow UI

Откройте в браузере: **http://localhost:8080**

- Логин: `admin`
- Пароль: `admin`

Вы должны увидеть DAG `bionicpro_etl_daily`.

## Этап 6: Тестирование ETL (15 минут)

### 6.1 Ручной запуск DAG

```bash
# Запустить DAG для конкретной даты
airflow dags trigger \
  --exec-date 2024-01-02 \
  bionicpro_etl_daily
```

### 6.2 Мониторинг выполнения

В Airflow UI:
1. Откройте `bionicpro_etl_daily`
2. Переходите на вкладку `Graph View`
3. Ждите выполнения всех задач (должны стать зелёными)

### 6.3 Проверка логов

```bash
# Посмотреть логи определённой задачи
airflow tasks logs \
  bionicpro_etl_daily \
  extract_crm_data \
  2024-01-02
```

### 6.4 Проверка результатов в ClickHouse

```bash
# После успешного запуска DAG проверьте данные:
clickhouse-client -d reports_db -q \
  "SELECT COUNT(*) FROM report_user_monthly_metrics;"

# Результат должен быть > 0
```

## Этап 7: Первый отчёт (5 минут)

### 7.1 Получение отчёта для пользователя

```bash
# Запрос в ClickHouse
clickhouse-client -d reports_db -q \
  "SELECT * FROM report_user_monthly_metrics 
   WHERE user_id = 1 
   FORMAT JSON"
```

### 7.2 Проверка протезов

```bash
# Все протезы для пользователя
clickhouse-client -d reports_db -q \
  "SELECT prosthetic_id, device_type, power_on_count, total_active_hours 
   FROM report_prosthetic_monthly_metrics 
   WHERE user_id = 1 
   FORMAT PrettyCompact"
```

## 🔍 Отладка проблем

### Проблема: "Connection refused" для PostgreSQL

**Решение:**
```bash
# Убедитесь, что PostgreSQL запущен
sudo systemctl status postgresql

# Или в Mac:
brew services list | grep postgres

# Или проверьте пароль:
psql -U postgres -c "SELECT version();"
```

### Проблема: DAG не появляется в Airflow

**Решение:**
```bash
# Проверьте синтаксис DAG файла
python -m py_compile ~/airflow/dags/airflow_etl_dag.py

# Перезагрузите Airflow
# (остановите Scheduler/Webserver и запустите снова)

# Проверьте переменные
airflow variables list
```

### Проблема: ClickHouse не отвечает

**Решение:**
```bash
# Проверьте, запущен ли контейнер
docker ps | grep clickhouse

# Если не запущен, запустите:
docker start clickhouse

# Проверьте подключение
clickhouse-client -q "SELECT 1;"
```

### Проблема: Нет данных в ClickHouse после DAG

**Решение:**
```bash
# Проверьте логи DAG
airflow tasks logs bionicpro_etl_daily load_to_clickhouse 2024-01-02

# Проверьте статус задач
airflow tasks list bionicpro_etl_daily

# Пересчитайте вручную:
airflow dags test bionicpro_etl_daily 2024-01-02
```

## ✅ Контрольный список

Перед сдачей проекта убедитесь:

- [ ] PostgreSQL запущен и содержит данные:
  - [ ] `crm_db` имеет 12 пользователей
  - [ ] `telemetry_db` имеет 456000 событий
  
- [ ] ClickHouse запущен и готов:
  - [ ] `reports_db` создана
  - [ ] Витрины созданы (2 таблицы)
  
- [ ] Airflow готов к работе:
  - [ ] DAG `bionicpro_etl_daily` видна в UI
  - [ ] Переменные установлены
  
- [ ] ETL выполнен успешно:
  - [ ] DAG запустился без ошибок
  - [ ] Все 5 задач выполнены (зелёные)
  - [ ] Данные загружены в ClickHouse

## 📊 Результаты

После успешного выполнения всех этапов:

✓ Вы получите **3 работающие БД** (CRM, Telemetry, Reports)
✓ Вы сгенерируете **2.5 года тестовых данных**
✓ Вы создадите **ETL-процесс** на Airflow
✓ Вы разработаете **2 витрины отчётов** в ClickHouse
✓ Вы сможете **запрашивать отчёты** в реальном времени

---

## 💡 Следующие шаги

После выполнения всех этапов:

1. **Развёртывание на боевом сервере**
   - Используйте Docker Compose для всех компонентов
   - Добавьте SSL сертификаты

2. **Интеграция с API**
   - Добавьте эндпоинт `/reports/{user_id}`
   - Реализуйте кеширование результатов

3. **Мониторинг**
   - Настройте Prometheus для метрик Airflow
   - Добавьте alerting для неудачных DAG

4. **Масштабирование** (для будущих спринтов)
   - Перейти на CDC (Debezium + Kafka) — Задание 4
   - Добавить S3/CDN для кеширования — Задание 3

---

**Успехов! 🚀**
