# Решение проблемы подключения к ClickHouse из DataGrip

## Проблема
При попытке подключиться к ClickHouse из DataGrip возникала ошибка:
```
Code: 194. DB::Exception: default: Authentication failed: password is incorrect
```

## Причина
Новые версии ClickHouse (25.10+) требуют явного указания пароля для пользователя `default`, даже если в переменной окружения `CLICKHOUSE_PASSWORD` указана пустая строка. JDBC-драйвер DataGrip не может корректно работать с пустым паролем.

## Решение

### 1. Создан файл конфигурации пользователя
Файл: `clickhouse_config/users.d/default-user.xml`

Этот файл устанавливает пароль `clickhouse_password` для пользователя `default`.

### 2. Обновлён docker-compose.yaml
Добавлены:
- Переменная окружения: `CLICKHOUSE_PASSWORD: "clickhouse_password"`
- Volume для конфигурации: `./clickhouse_config/users.d:/etc/clickhouse-server/users.d`
- Обновлён healthcheck с указанием пароля

### 3. Обновлены файлы с подключением к ClickHouse
- `reports_backend/main.py` — функция `get_clickhouse_client()`
- `reports_backend/import_olap_data.py` — константа `CLICKHOUSE_PASSWORD`
- `reports_backend/olap_query_examples.py` — функция `get_client()`

### 4. Перезапущен контейнер ClickHouse
```bash
bash restart_clickhouse.sh
```

## Параметры подключения для DataGrip

### HTTP-интерфейс (рекомендуется)
- **Host:** `localhost`
- **Port:** `8123`
- **Database:** `default`
- **User:** `default`
- **Password:** `clickhouse_password`

### Native-протокол (TCP)
- **Host:** `localhost`
- **Port:** `9431` ⚠️ **НЕ 9000!**
- **Database:** `default`
- **User:** `default`
- **Password:** `clickhouse_password`

## Проверка подключения

### Через curl (HTTP)
```bash
curl "http://default:clickhouse_password@localhost:8123/?query=SELECT%20version()"
```

### Через Docker (Native)
```bash
docker exec architecture-bionicpro-olap_db-1 clickhouse-client \
  --password clickhouse_password \
  --query "SELECT version()"
```

### Через clickhouse-client (если установлен на хосте)
```bash
clickhouse-client \
  --host localhost \
  --port 9431 \
  --password clickhouse_password \
  --query "SELECT version()"
```

## Настройка в DataGrip

1. Откройте DataGrip
2. Нажмите **File → New → Data Source → ClickHouse**
3. Заполните параметры:
   - **Host:** `localhost`
   - **Port:** `8123`
   - **Database:** `default`
   - **User:** `default`
   - **Password:** `clickhouse_password`
4. Нажмите **Test Connection** — должно появиться сообщение об успешном подключении
5. Нажмите **OK**

## Доступные таблицы

После подключения вы увидите следующие таблицы:
- `users` — пользователи из CRM-системы (1000 записей)
- `telemetry_events` — телеметрические данные с бионических протезов
- `emg_sensor_data` — данные с EMG-сенсоров

## Примеры запросов

```sql
-- Проверка версии
SELECT version();

-- Количество пользователей
SELECT COUNT(*) FROM users;

-- Количество событий телеметрии
SELECT COUNT(*) FROM telemetry_events;

-- Топ-5 пользователей по количеству событий
SELECT 
    u.name,
    COUNT(t.id) as events_count
FROM telemetry_events t
JOIN users u ON t.user_id = u.user_id
GROUP BY u.name
ORDER BY events_count DESC
LIMIT 5;
```

## Важные замечания

1. **Пароль для разработки:** `clickhouse_password` — это пароль для локальной разработки. В продакшене используйте более безопасный пароль и храните его в переменных окружения или секретах.

2. **Порт Native-протокола:** Обратите внимание, что native-порт ClickHouse (9000) проброшен на хост как **9431**, а не 9000. Это сделано для избежания конфликтов с другими сервисами.

3. **HTTP vs Native:** Для DataGrip рекомендуется использовать HTTP-интерфейс (порт 8123), так как он более стабилен и поддерживает все функции JDBC-драйвера.

4. **Перезапуск после изменений:** Если вы меняете конфигурацию пользователей, необходимо перезапустить контейнер:
   ```bash
   bash restart_clickhouse.sh
   ```

## Полезные файлы

- `CLICKHOUSE_CONNECTION.md` — подробная инструкция по подключению
- `restart_clickhouse.sh` — скрипт для перезапуска ClickHouse
- `clickhouse_quick_test.sh` — скрипт для быстрой проверки подключения
- `clickhouse_config/users.d/default-user.xml` — конфигурация пользователя

## Статус
✅ **Проблема решена.** ClickHouse успешно запущен и доступен для подключения из DataGrip.
