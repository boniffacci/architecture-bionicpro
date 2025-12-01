"""
Интеграционный тест для проверки создания таблиц в схеме default при запуске reports_api.
"""

import subprocess
import time
import pytest


def test_default_schema_tables_created_on_startup():
    """
    Тест проверяет, что reports_api создаёт таблицы в схеме default при запуске.
    
    Этот тест:
    1. Удаляет таблицы из схемы default
    2. Перезапускает reports_api
    3. Проверяет, что таблицы созданы
    """
    project_dir = "/home/felix/Projects/yandex_swa_pro/architecture-bionicpro"
    
    print("\n" + "=" * 80)
    print("ТЕСТ: Reports API должен создавать таблицы в схеме default при запуске")
    print("=" * 80)
    
    # Шаг 1: Удаляем таблицы из схемы default
    print("\n1. Удаляем таблицы из схемы default...")
    subprocess.run(
        ["docker", "compose", "exec", "-T", "olap-db",
         "clickhouse-client", "--password=clickhouse_password",
         "--query=DROP TABLE IF EXISTS default.users"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["docker", "compose", "exec", "-T", "olap-db",
         "clickhouse-client", "--password=clickhouse_password",
         "--query=DROP TABLE IF EXISTS default.telemetry_events"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )
    print("   ✓ Таблицы удалены")
    
    # Шаг 2: Проверяем, что таблиц нет
    print("\n2. Проверяем, что таблиц нет...")
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "olap-db",
         "clickhouse-client", "--password=clickhouse_password",
         "--query=SHOW TABLES FROM default"],
        cwd=project_dir,
        check=True,
        capture_output=True,
        text=True
    )
    tables = result.stdout.strip().split('\n') if result.stdout.strip() else []
    print(f"   Таблицы в схеме default: {tables}")
    assert "users" not in tables, "Таблица users не должна существовать"
    assert "telemetry_events" not in tables, "Таблица telemetry_events не должна существовать"
    print("   ✓ Таблиц нет")
    
    # Шаг 3: Перезапускаем reports-api
    print("\n3. Перезапускаем reports-api...")
    subprocess.run(
        ["docker", "compose", "restart", "reports-api"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )
    print("   ✓ reports-api перезапущен")
    
    # Шаг 4: Ждём запуска
    print("\n4. Ожидание запуска reports-api...")
    time.sleep(15)
    
    # Проверяем, что контейнер запущен
    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "json", "reports-api"],
        cwd=project_dir,
        check=True,
        capture_output=True,
        text=True
    )
    
    import json
    container_info = json.loads(result.stdout.strip())
    container_state = container_info.get("State", "")
    
    print(f"   Статус контейнера: {container_state}")
    assert container_state == "running", f"Контейнер должен быть в статусе running, текущий статус: {container_state}"
    print("   ✓ Контейнер запущен")
    
    # Шаг 5: Проверяем логи
    print("\n5. Проверяем логи reports-api...")
    logs_result = subprocess.run(
        ["docker", "compose", "logs", "reports-api", "--tail=100"],
        cwd=project_dir,
        check=True,
        capture_output=True,
        text=True
    )
    
    logs = logs_result.stdout
    
    # Проверяем, что в логах есть инициализация схемы default
    assert "Инициализация схемы default в ClickHouse..." in logs, \
        "В логах должна быть инициализация схемы default"
    assert "Схема default успешно инициализирована" in logs, \
        "В логах должно быть сообщение об успешной инициализации схемы default"
    
    print("   ✓ Логи содержат информацию об инициализации схемы default")
    
    # Шаг 6: Проверяем, что таблицы созданы
    print("\n6. Проверяем, что таблицы созданы...")
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "olap-db",
         "clickhouse-client", "--password=clickhouse_password",
         "--query=SHOW TABLES FROM default"],
        cwd=project_dir,
        check=True,
        capture_output=True,
        text=True
    )
    
    tables = result.stdout.strip().split('\n')
    print(f"   Таблицы в схеме default: {tables}")
    
    assert "users" in tables, "Таблица users должна быть создана"
    assert "telemetry_events" in tables, "Таблица telemetry_events должна быть создана"
    print("   ✓ Таблицы созданы")
    
    # Шаг 7: Проверяем структуру таблицы users
    print("\n7. Проверяем структуру таблицы users...")
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "olap-db",
         "clickhouse-client", "--password=clickhouse_password",
         "--query=DESCRIBE TABLE default.users"],
        cwd=project_dir,
        check=True,
        capture_output=True,
        text=True
    )
    
    users_structure = result.stdout
    print(f"   Структура таблицы users:\n{users_structure}")
    
    # Проверяем наличие основных полей
    assert "user_id" in users_structure, "Таблица users должна содержать поле user_id"
    assert "user_uuid" in users_structure, "Таблица users должна содержать поле user_uuid"
    assert "name" in users_structure, "Таблица users должна содержать поле name"
    assert "email" in users_structure, "Таблица users должна содержать поле email"
    print("   ✓ Структура таблицы users корректна")
    
    # Шаг 8: Проверяем структуру таблицы telemetry_events
    print("\n8. Проверяем структуру таблицы telemetry_events...")
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "olap-db",
         "clickhouse-client", "--password=clickhouse_password",
         "--query=DESCRIBE TABLE default.telemetry_events"],
        cwd=project_dir,
        check=True,
        capture_output=True,
        text=True
    )
    
    telemetry_structure = result.stdout
    print(f"   Структура таблицы telemetry_events:\n{telemetry_structure}")
    
    # Проверяем наличие основных полей
    assert "id" in telemetry_structure, "Таблица telemetry_events должна содержать поле id"
    assert "event_uuid" in telemetry_structure, "Таблица telemetry_events должна содержать поле event_uuid"
    assert "user_uuid" in telemetry_structure, "Таблица telemetry_events должна содержать поле user_uuid"
    assert "prosthesis_type" in telemetry_structure, "Таблица telemetry_events должна содержать поле prosthesis_type"
    assert "created_ts" in telemetry_structure, "Таблица telemetry_events должна содержать поле created_ts"
    print("   ✓ Структура таблицы telemetry_events корректна")
    
    print("\n" + "=" * 80)
    print("✓ ТЕСТ ПРОЙДЕН: Таблицы в схеме default создаются при запуске reports_api")
    print("=" * 80)


if __name__ == "__main__":
    test_default_schema_tables_created_on_startup()
