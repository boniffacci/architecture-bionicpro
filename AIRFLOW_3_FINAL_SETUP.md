# Финальная настройка Apache Airflow 3.1.3

## Ключевые изменения для Airflow 3.x

### 1. Архитектура

В Airflow 3.x парсинг DAG'ов вынесен в отдельный компонент **dag-processor**.

**Компоненты:**
- `airflow-db` - PostgreSQL для метаданных
- `airflow-webserver` → `airflow-api-server` - веб-интерфейс (команда `api-server`)
- **`airflow-dag-processor`** - парсер DAG'ов (новый компонент)
- `airflow-scheduler` - планировщик задач

### 2. Docker Compose структура

```yaml
services:
  airflow-webserver:
    command: api-server  # Вместо webserver
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8080/ || exit 1"]

  airflow-dag-processor:  # Новый сервис
    command: dag-processor
    volumes:
      - ./dags:/opt/airflow/dags
    healthcheck:
      test: ["CMD-SHELL", "pgrep -f 'airflow dag-processor' || exit 1"]

  airflow-scheduler:
    depends_on:
      airflow-dag-processor:
        condition: service_healthy  # Ждём готовности dag-processor
```

### 3. Изменения в DAG (import_olap_data.py)

#### Импорты
```python
try:
    from airflow.providers.standard.operators.python import PythonOperator
except ImportError:
    from airflow.operators.python import PythonOperator  # Fallback
```

#### Параметры DAG
```python
dag = DAG(
    'import_olap_data_monthly',
    schedule='0 1 1 * *',  # schedule вместо schedule_interval
    ...
)
```

#### Оператор
```python
import_task = PythonOperator(
    task_id='import_previous_month_data',
    python_callable=import_previous_month,
    # provide_context удалён (контекст передаётся автоматически)
    dag=dag
)
```

### 4. Управление DAG'ами через CLI

В Airflow 3.x REST API изменился, используем CLI:

```bash
# Список DAG'ов
docker exec airflow-dag-processor airflow dags list

# Активация DAG
docker exec airflow-dag-processor airflow dags unpause import_olap_data_monthly

# Триггер DAG
docker exec airflow-scheduler airflow dags trigger import_olap_data_monthly

# Список запусков
docker exec airflow-scheduler airflow dags list-runs -d import_olap_data_monthly
```

### 5. Проверка работоспособности

#### Проверка DAG локально
```bash
docker exec airflow-dag-processor python -c "
import sys
sys.path.insert(0, '/opt/airflow/dags')
import import_olap_data
print('DAG ID:', import_olap_data.dag.dag_id)
print('Schedule:', import_olap_data.dag.schedule)
"
```

#### Проверка через CLI
```bash
# Проверка всех компонентов
docker ps --filter "name=airflow" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Проверка логов dag-processor
docker logs airflow-dag-processor --tail 50

# Проверка логов scheduler
docker logs airflow-scheduler --tail 50
```

#### Проверка через UI
1. Откройте http://localhost:8082
2. Проверьте наличие DAG `import_olap_data_monthly`
3. Убедитесь, что DAG корректно распарсен

### 6. Порты и URL

| Компонент           | Порт  | URL                             |
|---------------------|-------|---------------------------------|
| Airflow UI          | 8082  | http://localhost:8082           |
| Airflow DB          | 5446  | postgresql://localhost:5446     |
| CRM API             | 3001  | http://localhost:3001           |
| Telemetry API       | 3002  | http://localhost:3002           |
| Reports API         | 3003  | http://localhost:3003           |
| ClickHouse HTTP     | 8123  | http://localhost:8123           |

### 7. Troubleshooting

#### DAG не появляется в списке

1. **Проверьте dag-processor работает:**
   ```bash
   docker exec airflow-dag-processor pgrep -f "airflow dag-processor"
   ```

2. **Проверьте логи dag-processor:**
   ```bash
   docker logs airflow-dag-processor 2>&1 | grep -i "import_olap\|error"
   ```

3. **Проверьте синтаксис DAG:**
   ```bash
   docker exec airflow-dag-processor python /opt/airflow/dags/import_olap_data.py
   ```

4. **Проверьте ошибки импорта:**
   ```bash
   docker exec airflow-dag-processor airflow dags list-import-errors
   ```

#### dag-processor не запускается

1. **Проверьте наличие файла:**
   ```bash
   docker exec airflow-dag-processor ls -la /opt/airflow/dags/
   ```

2. **Проверьте переменные окружения:**
   ```bash
   docker exec airflow-dag-processor env | grep AIRFLOW
   ```

3. **Перезапустите dag-processor:**
   ```bash
   docker restart airflow-dag-processor
   ```

#### Контейнер падает при старте

1. **Проверьте логи:**
   ```bash
   docker logs airflow-dag-processor --tail 100
   docker logs airflow-scheduler --tail 100
   ```

2. **Проверьте зависимости:**
   ```bash
   docker exec airflow-dag-processor pip list | grep -E "airflow|clickhouse|sqlmodel"
   ```

### 8. Последовательность запуска

```bash
# 1. Остановка и очистка
docker compose down -v

# 2. Сборка образов
docker compose build

# 3. Запуск всех сервисов
docker compose up -d

# 4. Проверка статуса
docker ps --filter "name=airflow"

# 5. Ожидание готовности (примерно 2-3 минуты)
watch -n 5 'docker inspect airflow-dag-processor --format="{{.State.Health.Status}}"'

# 6. Проверка DAG'ов
docker exec airflow-dag-processor airflow dags list
```

### 9. Интеграционный тест

Тест `test_airflow_integration.py` автоматически:
1. Выполняет `docker compose down -v && build && up -d`
2. Ждёт готовности всех контейнеров (включая `airflow-dag-processor`)
3. Проверяет наличие DAG через CLI
4. Генерирует тестовые данные
5. Активирует и триггерит DAG
6. Проверяет данные в ClickHouse

**Запуск:**
```bash
.venv/bin/python tests/test_airflow_integration.py
```

### 10. Мониторинг

```bash
# Статус всех Airflow-компонентов
docker ps --filter "name=airflow" --format "table {{.Names}}\t{{.Status}}"

# Логи всех компонентов
docker compose logs -f airflow-dag-processor airflow-scheduler airflow-webserver

# Проверка метаданных в БД
docker exec airflow-db psql -U airflow_user -d airflow_db -c "SELECT dag_id, is_paused FROM dag;"
```

## Ссылки

- [Airflow 3.0 Release Notes](https://airflow.apache.org/docs/apache-airflow/stable/release_notes.html)
- [Migration Guide 2.x → 3.x](https://airflow.apache.org/docs/apache-airflow/stable/migration-guide-2-to-3.html)
- [DAG Processor Architecture](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/dag-processor.html)
