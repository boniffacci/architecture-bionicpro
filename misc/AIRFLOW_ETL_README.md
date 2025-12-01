# Руководство по Apache Airflow ETL

## Обзор

В проект добавлена интеграция с Apache Airflow 3.1.3 для автоматизации ETL-процесса импорта данных из PostgreSQL в ClickHouse.

## Архитектура

### Компоненты

1. **Apache Airflow** (3 контейнера):
   - `airflow-db` - PostgreSQL 17 для метаданных Airflow
   - `airflow-webserver` - Веб-интерфейс на порту `8082`
   - `airflow-scheduler` - Планировщик для выполнения DAG'ов

2. **DAG**: `import_olap_data_monthly`
   - Расположение: `/dags/import_olap_data.py`
   - Запускается: 1-го числа каждого месяца в 01:00 UTC
   - Start date: 1 января 2025 года
   - Catchup: включен (для загрузки исторических данных за 2025 год)

3. **Схемы ClickHouse**:
   - `default.users` - ReplacingMergeTree (для OLAP-аналитики)
   - `default.telemetry_events` - ReplacingMergeTree с партиционированием по годам/месяцам
   - `debezium.users` - ReplacingMergeTree (для real-time CDC через Kafka)
   - `debezium.telemetry_events` - ReplacingMergeTree (для real-time CDC через Kafka)

## Учётные данные

### Airflow
- **URL**: http://localhost:8082
- **Логин**: `airflow_admin`
- **Пароль**: `airflow_password`

### ClickHouse
- **HTTP порт**: 8123
- **Native порт**: 9431
- **Логин**: `default`
- **Пароль**: `clickhouse_password`

## Запуск

### 1. Полный перезапуск с очисткой данных

```bash
# Останавливаем и удаляем все контейнеры и volumes
docker compose down -v

# Собираем образы (обязательно, т.к. добавлен новый Dockerfile для Airflow)
docker compose build

# Запускаем все сервисы
docker compose up -d

# Проверяем статус контейнеров
docker ps
```

### 2. Проверка готовности Airflow

```bash
# Проверка здоровья Airflow Webserver
docker inspect airflow-webserver --format='{{.State.Health.Status}}'

# Проверка здоровья Airflow Scheduler
docker inspect airflow-scheduler --format='{{.State.Health.Status}}'

# Просмотр логов
docker logs airflow-webserver
docker logs airflow-scheduler
```

### 3. Доступ к Airflow UI

Откройте браузер и перейдите на:
- http://localhost:8082

Войдите с учётными данными:
- Логин: `airflow_admin`
- Пароль: `airflow_password`

## Использование фронтенда

На фронтенде (http://localhost:3000) добавлен новый блок **ETL-операции** с двумя кнопками:

### 1. Сгенерировать юзеров и события

Вызывает эндпоинты:
- `POST http://localhost:3001/populate_base` (CRM API)
- `POST http://localhost:3002/populate_base` (Telemetry API)

Генерирует:
- 1000 пользователей в CRM БД
- 10000 событий в Telemetry БД

### 2. Запустить ETL-процесс

Выполняет:
1. Активирует DAG `import_olap_data_monthly` в Airflow (снимает паузу)
2. Триггерит новый DAG Run
3. Открывает Airflow UI в новой вкладке

После запуска ETL-процесса можно отслеживать выполнение в Airflow UI.

## Проверка данных в ClickHouse

### Через CLI

```bash
# Подключение к ClickHouse
docker exec -it olap-db clickhouse-client --password clickhouse_password

# Проверка количества пользователей в схеме default
SELECT count() FROM default.users;

# Проверка количества событий в схеме default
SELECT count() FROM default.telemetry_events;

# Проверка партиций
SELECT 
    partition, 
    count() as events_count,
    min(created_ts) as min_date,
    max(created_ts) as max_date
FROM default.telemetry_events
GROUP BY partition
ORDER BY partition;
```

### Через HTTP API

```bash
# Проверка пользователей
curl -X POST 'http://localhost:8123/?user=default&password=clickhouse_password&query=SELECT%20count()%20FROM%20default.users'

# Проверка событий
curl -X POST 'http://localhost:8123/?user=default&password=clickhouse_password&query=SELECT%20count()%20FROM%20default.telemetry_events'
```

## Признак кэша в отчётах

В отчётах (блок "Запросы к reports_api") теперь отображается признак:
- 📦 **Из кэша** - отчёт загружен из MinIO
- 🔄 **Не из кэша** - отчёт сгенерирован заново из ClickHouse

Первый запрос обычно генерируется заново, повторные запросы с теми же параметрами берутся из кэша.

## Тестирование

### Интеграционный тест Airflow

```bash
# Запуск теста test_airflow_integration.py
.venv/bin/python tests/test_airflow_integration.py
```

Тест выполняет:
1. `docker compose down -v`
2. `docker compose build`
3. `docker compose up -d`
4. Проверка готовности всех контейнеров
5. Проверка подключения к Airflow REST API
6. Проверка наличия DAG `import_olap_data_monthly`
7. Генерация данных через `/populate_base`
8. Активация DAG
9. Ожидание успешного выполнения Task Instance
10. Проверка данных в ClickHouse (>= 1000 пользователей, >= 10000 событий)

### Playwright-тест фронтенда

```bash
# Запуск теста test_frontend_etl.py
.venv/bin/python -m pytest tests/test_frontend_etl.py -v -s
```

Тест проверяет:
1. Наличие блока ETL-операций
2. Работу кнопки "Сгенерировать юзеров и события"
3. Работу кнопки "Запустить ETL-процесс"
4. Отображение признака кэша в отчётах

## Troubleshooting

### Airflow не запускается

Проверьте логи:
```bash
docker logs airflow-webserver
docker logs airflow-scheduler
docker logs airflow-init
```

### DAG не появляется в UI

1. Проверьте, что файл `dags/import_olap_data.py` смонтирован в контейнер:
   ```bash
   docker exec airflow-webserver ls -la /opt/airflow/dags/
   ```

2. Проверьте синтаксис DAG:
   ```bash
   docker exec airflow-webserver python /opt/airflow/dags/import_olap_data.py
   ```

3. Проверьте логи Scheduler:
   ```bash
   docker logs airflow-scheduler | grep import_olap_data
   ```

### Task Instance падает с ошибкой

1. Проверьте подключение к ClickHouse:
   ```bash
   docker exec airflow-scheduler curl -v http://olap-db:8123
   ```

2. Проверьте подключение к PostgreSQL (CRM DB):
   ```bash
   docker exec airflow-scheduler nc -zv crm-db 5432
   ```

3. Проверьте подключение к PostgreSQL (Telemetry DB):
   ```bash
   docker exec airflow-scheduler nc -zv telemetry-db 5432
   ```

4. Проверьте логи Task Instance в Airflow UI

### ClickHouse не содержит данных

1. Проверьте, что в PostgreSQL есть данные:
   ```bash
   docker exec crm-db psql -U crm_user -d crm_db -c "SELECT count(*) FROM users;"
   docker exec telemetry-db psql -U telemetry_user -d telemetry_db -c "SELECT count(*) FROM telemetry_events;"
   ```

2. Проверьте таблицы в ClickHouse:
   ```bash
   docker exec olap-db clickhouse-client --password clickhouse_password --query "SHOW TABLES FROM default"
   docker exec olap-db clickhouse-client --password clickhouse_password --query "SHOW TABLES FROM debezium"
   ```

3. Проверьте схему таблиц:
   ```bash
   docker exec olap-db clickhouse-client --password clickhouse_password --query "SHOW CREATE TABLE default.users"
   docker exec olap-db clickhouse-client --password clickhouse_password --query "SHOW CREATE TABLE default.telemetry_events"
   ```

## Структура файлов

```
.
├── airflow/
│   ├── Dockerfile                     # Кастомный образ Airflow с зависимостями
│   └── init_airflow.sh                # Скрипт инициализации БД и создания админа
├── dags/
│   └── import_olap_data.py            # DAG для импорта данных
├── tests/
│   ├── test_airflow_integration.py    # Интеграционный тест Airflow
│   └── test_frontend_etl.py           # Playwright-тест фронтенда
├── bionicpro_frontend/
│   └── src/
│       └── App.tsx                    # Обновлённый фронтенд с ETL-кнопками
├── docker-compose.yaml                # Обновлённый с Airflow-сервисами
└── AIRFLOW_ETL_README.md              # Это руководство
```

## Мониторинг

### Airflow UI
- **URL**: http://localhost:8082
- Просмотр DAG Runs, Task Instances, логов выполнения

### Kafka UI
- **URL**: http://localhost:8084
- Мониторинг топиков Debezium для real-time CDC

### Debezium UI
- **URL**: http://localhost:8088
- Управление Debezium-коннекторами

## Дополнительные ресурсы

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [ClickHouse Documentation](https://clickhouse.com/docs/)
- [Debezium Documentation](https://debezium.io/documentation/)
