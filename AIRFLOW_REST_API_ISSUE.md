# Проблема с REST API в Airflow 3.x

## Обнаруженная проблема

При попытке использовать REST API v2 в Airflow 3.1.3 с FAB Auth Manager, Basic Authentication не работает корректно:

```bash
curl -u airflow_admin:airflow_password http://localhost:8082/api/v2/dags
# Возвращает: {"detail":"Not authenticated"}
```

## Причина

В Airflow 3.x API v2 использует новую систему аутентификации на основе токенов (JWT), а не Basic Auth. Настройка `AIRFLOW__API__AUTH_BACKENDS` для Basic Auth не применяется к API v2.

## Решение для интеграционных тестов

Используем **docker exec** для управления DAG'ами через Airflow CLI, что является стандартной практикой:

```bash
# Проверка наличия DAG
docker exec airflow-dag-processor airflow dags list

# Активация DAG
docker exec airflow-dag-processor airflow dags unpause import_olap_data_monthly

# Триггер DAG
docker exec airflow-scheduler airflow dags trigger import_olap_data_monthly

# Прямой запуск задачи (для тестов)
docker exec airflow-scheduler airflow tasks test import_olap_data_monthly import_previous_month_data 2025-01-01
```

## Альтернативы (не реализованы)

1. **Настройка JWT токенов** - требует сложной конфигурации OAuth2/OIDC
2. **Использование API v1** - удалён в Airflow 3.x
3. **Отключение аутентификации** - небезопасно и не работает в 3.x

## Вывод

Для production и тестовых окружений рекомендуется использовать Airflow CLI через docker exec, а не REST API.
