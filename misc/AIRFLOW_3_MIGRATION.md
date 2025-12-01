# Миграция на Apache Airflow 3.x

## Изменения, внесённые для совместимости с Airflow 3.1.3

### 1. Docker Compose изменения

#### `docker-compose.yaml`

**Webserver команда:**
- Изменено: `webserver` → `api-server`
- Причина: В Airflow 3.x команда `webserver` удалена, используется `api-server`

**Healthcheck для Webserver:**
- Изменено: `curl -f http://localhost:8080/health` → `curl -f http://localhost:8080/`
- Причина: Эндпоинт `/health` не существует в Airflow 3.x, проверяем корневой путь

### 2. Изменения в import_olap_data.py

#### Импорты операторов

**Было:**
```python
from airflow.operators.python import PythonOperator
```

**Стало:**
```python
try:
    from airflow.providers.standard.operators.python import PythonOperator
except ImportError:
    from airflow.operators.python import PythonOperator  # Fallback для Airflow 2.x
```

**Причина:** В Airflow 3.x операторы перенесены в провайдеры (`airflow-providers-standard`)

#### Параметр schedule

**Было:**
```python
dag = DAG(
    'import_olap_data_monthly',
    schedule_interval='0 1 1 * *',
    ...
)
```

**Стало:**
```python
dag = DAG(
    'import_olap_data_monthly',
    schedule='0 1 1 * *',  # schedule вместо schedule_interval
    ...
)
```

**Причина:** В Airflow 3.x параметр `schedule_interval` переименован в `schedule`

#### Параметр provide_context

**Было:**
```python
import_task = PythonOperator(
    task_id='import_previous_month_data',
    python_callable=import_previous_month,
    provide_context=True,  # <-- удалён
    dag=dag
)
```

**Стало:**
```python
import_task = PythonOperator(
    task_id='import_previous_month_data',
    python_callable=import_previous_month,
    # provide_context удалён (контекст передаётся автоматически)
    dag=dag
)
```

**Причина:** В Airflow 3.x параметр `provide_context` устарел и удалён

#### Блок __main__ 

**Было:**
```python
if __name__ == "__main__":
    if dag is not None:
        dag.test(execution_date=datetime.now(timezone.utc), run_conf=None)
    else:
        # argparse код
```

**Стало:**
```python
if __name__ == "__main__":
    # Только argparse, без dag.test()
    parser = argparse.ArgumentParser(...)
    ...
```

**Причина:** `dag.test()` изменил API в Airflow 3.x

### 3. Изменения в test_airflow_integration.py

#### REST API версия

**Было:**
```python
AIRFLOW_API_URL = "http://localhost:8082/api/v1"
```

**Стало:**
```python
AIRFLOW_API_URL = "http://localhost:8082/api/v2"  # API v2 в Airflow 3.x
```

**Причина:** В Airflow 3.x API v1 удалён, используется API v2

#### Управление DAG'ами

**Было:** REST API вызовы для управления DAG'ами

**Стало:** Использование Airflow CLI через `docker exec`

**Примеры:**
```bash
# Проверка наличия DAG
docker exec airflow-scheduler airflow dags list

# Активация DAG
docker exec airflow-scheduler airflow dags unpause import_olap_data_monthly

# Триггер DAG
docker exec airflow-scheduler airflow dags trigger import_olap_data_monthly

# Список запусков
docker exec airflow-scheduler airflow dags list-runs -d import_olap_data_monthly
```

**Причина:** В Airflow 3.x Simple Auth Manager не поддерживает REST API аутентификацию

### 4. Известные проблемы

#### DAG не обнаруживается scheduler'ом

**Симптомы:**
- `airflow dags list` возвращает "No data found"
- DAG корректно импортируется через `python import_olap_data.py`
- Нет ошибок в `airflow dags list-import-errors`

**Возможные причины:**
1. В Airflow 3.x парсинг DAG'ов отделён от scheduler'а в отдельный процесс `dag-processor`
2. Требуется явная регистрация DAG в глобальной области видимости

**Решения (ещё в процессе):**
- Добавить отдельный контейнер `airflow-dag-processor`
- Использовать `airflow standalone` вместо раздельных webserver/scheduler
- Проверить права доступа к папке `/opt/airflow/dags`

#### Конфликт зависимостей SQLAlchemy

**Предупреждение:**
```
apache-airflow-providers-fab 3.0.1 requires sqlalchemy<2
```

**Статус:** Не критично, Airflow продолжает работать

## Тестирование изменений

### Проверка DAG локально

```bash
# Проверка синтаксиса DAG
docker exec airflow-scheduler python /opt/airflow/dags/import_olap_data.py

# Проверка импорта DAG
docker exec airflow-scheduler python -c "import sys; sys.path.insert(0, '/opt/airflow/dags'); import import_olap_data; print('DAG ID:', import_olap_data.dag.dag_id)"
```

### Проверка через Airflow CLI

```bash
# Список DAG'ов
docker exec airflow-scheduler airflow dags list

# Проверка ошибок импорта
docker exec airflow-scheduler airflow dags list-import-errors

# Информация о конкретном DAG
docker exec airflow-scheduler airflow dags show import_olap_data_monthly
```

### Проверка через UI

1. Откройте http://localhost:8082
2. Войдите с учётными данными (если требуется)
3. Проверьте список DAG'ов на главной странице

## Полезные ссылки

- [Airflow 3.0 Release Notes](https://airflow.apache.org/docs/apache-airflow/stable/release_notes.html#airflow-3-0-0)
- [Migration Guide Airflow 2.x to 3.x](https://airflow.apache.org/docs/apache-airflow/stable/migration-guide-2-to-3.html)
- [Airflow 3.x API Reference](https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html)
