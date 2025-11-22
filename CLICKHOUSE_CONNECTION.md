# Инструкция по подключению к ClickHouse из DataGrip

## Проблема
ClickHouse запущен в Docker-контейнере, и порты пробрасываются не на стандартные значения.

## Параметры подключения

### Вариант 1: HTTP-интерфейс (рекомендуется)

DataGrip поддерживает подключение к ClickHouse через HTTP-интерфейс (JDBC/ODBC драйвер).

**Параметры подключения:**
- **Driver:** ClickHouse (HTTP)
- **Host:** `localhost`
- **Port:** `8123`
- **Database:** `default`
- **User:** `default`
- **Password:** `clickhouse_password`

**URL для JDBC:**
```
jdbc:clickhouse://localhost:8123/default
```

### Вариант 2: Native-протокол (TCP)

Если используете native-драйвер ClickHouse:

**Параметры подключения:**
- **Driver:** ClickHouse (Native)
- **Host:** `localhost`
- **Port:** `9431` ⚠️ **НЕ 9000!** (порт проброшен на 9431)
- **Database:** `default`
- **User:** `default`
- **Password:** `clickhouse_password`

## Проверка подключения из командной строки

### HTTP-интерфейс
```bash
curl "http://localhost:8123/?query=SELECT%20version()"
```

### Native-протокол (через Docker)
```bash
docker exec architecture-bionicpro-olap_db-1 clickhouse-client --password clickhouse_password --query "SELECT version()"
```

### Native-протокол (с хоста, если установлен clickhouse-client)
```bash
clickhouse-client --host localhost --port 9431 --password clickhouse_password --query "SELECT version()"
```

## Настройка в DataGrip

1. Откройте DataGrip
2. Создайте новое подключение: **File → New → Data Source → ClickHouse**
3. Выберите драйвер:
   - Для HTTP: `ClickHouse` (обычный драйвер)
   - Для Native: `ClickHouse (com.clickhouse)` или `ClickHouse (ru.yandex.clickhouse)`
4. Введите параметры подключения (см. выше)
5. Нажмите **Test Connection**

## Таблицы в БД

После успешного подключения вы увидите следующие таблицы:
- `users` — пользователи из CRM-системы
- `telemetry_events` — телеметрические данные с бионических протезов

## Примеры запросов

```sql
-- Проверка версии
SELECT version();

-- Список таблиц
SHOW TABLES;

-- Количество пользователей
SELECT COUNT(*) FROM users;

-- Количество событий телеметрии
SELECT COUNT(*) FROM telemetry_events;

-- Статистика по пользователям
SELECT 
    u.name,
    u.email,
    COUNT(t.id) as events_count,
    AVG(t.signal_amplitude) as avg_amplitude
FROM telemetry_events t
JOIN users u ON t.user_id = u.user_id
GROUP BY u.name, u.email
ORDER BY events_count DESC
LIMIT 10;
```

## Порты в docker-compose.yaml

```yaml
olap_db:
  image: clickhouse/clickhouse-server:latest
  ports:
    - "8123:8123"   # HTTP-интерфейс (для DataGrip, JDBC, ODBC)
    - "9431:9000"   # Native-протокол (TCP) — проброшен на 9431!
```

## Troubleshooting

### Ошибка "Connection refused"
- Проверьте, что контейнер запущен: `docker ps | grep clickhouse`
- Проверьте, что порты открыты: `netstat -tlnp | grep -E "(8123|9431)"`

### Ошибка "Authentication failed"
- Убедитесь, что используете пароль: `clickhouse_password`
- Пользователь по умолчанию: `default`

### Ошибка "Database does not exist"
- Используйте базу данных `default`
- Или создайте новую: `CREATE DATABASE my_database`
