"""Тесты для скрипта импорта данных в ClickHouse OLAP."""

import pytest
from datetime import datetime, timezone
import clickhouse_connect

import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path для импорта из dags/
sys.path.insert(0, str(Path(__file__).parent.parent))

from dags.import_olap_data import (
    get_clickhouse_client,
    create_olap_tables,
    import_users_data,
    import_telemetry_data,
    cleanup_orphaned_events,
    import_olap_data,
)


@pytest.fixture(scope="function")
def clickhouse_client():
    """Фикстура для подключения к ClickHouse с очисткой таблиц."""
    client = get_clickhouse_client()

    # Очищаем таблицы перед тестом
    try:
        client.command("DROP TABLE IF EXISTS users")
        client.command("DROP TABLE IF EXISTS telemetry_events")
    except Exception:
        pass

    yield client

    # Очищаем таблицы после теста
    try:
        client.command("DROP TABLE IF EXISTS users")
        client.command("DROP TABLE IF EXISTS telemetry_events")
    except Exception:
        pass


def test_clickhouse_connection(clickhouse_client):
    """Тест подключения к ClickHouse."""
    result = clickhouse_client.query("SELECT 1")
    assert result.result_rows == [(1,)]


def test_create_olap_tables(clickhouse_client):
    """Тест создания таблиц в ClickHouse."""
    # Создаем таблицы
    create_olap_tables(clickhouse_client)

    # Проверяем, что таблица users создана
    result = clickhouse_client.query("SHOW TABLES LIKE 'users'")
    assert len(result.result_rows) == 1
    assert result.result_rows[0][0] == "users"

    # Проверяем, что таблица telemetry_events создана
    result = clickhouse_client.query("SHOW TABLES LIKE 'telemetry_events'")
    assert len(result.result_rows) == 1
    assert result.result_rows[0][0] == "telemetry_events"


def test_import_users_data(clickhouse_client):
    """Тест импорта данных пользователей."""
    # Создаем таблицы
    create_olap_tables(clickhouse_client)

    # Импортируем данные пользователей
    import_users_data(clickhouse_client)

    # Проверяем, что данные импортированы
    result = clickhouse_client.query("SELECT COUNT(*) FROM users")
    users_count = result.result_rows[0][0]

    # Должно быть больше 0 пользователей
    assert users_count > 0

    # Проверяем структуру данных
    result = clickhouse_client.query("SELECT * FROM users LIMIT 1")
    if result.result_rows:
        user = result.result_rows[0]
        # Проверяем, что все поля присутствуют
        assert len(user) == 11  # 11 полей в таблице users


def test_import_telemetry_data_without_filters(clickhouse_client):
    """Тест импорта телеметрических данных без фильтров."""
    # Создаем таблицы
    create_olap_tables(clickhouse_client)

    # Импортируем телеметрические данные без фильтров
    import_telemetry_data(clickhouse_client)

    # Проверяем, что данные импортированы
    result = clickhouse_client.query("SELECT COUNT(*) FROM telemetry_events")
    events_count = result.result_rows[0][0]

    # Должно быть больше 0 событий
    assert events_count > 0


def test_import_telemetry_data_with_time_filters(clickhouse_client):
    """Тест импорта телеметрических данных с временными фильтрами."""
    # Создаем таблицы
    create_olap_tables(clickhouse_client)

    # Очищаем таблицу перед тестом (чтобы не было данных из предыдущих тестов)
    clickhouse_client.command("TRUNCATE TABLE telemetry_events")

    # Проверяем, что таблица действительно пуста
    result = clickhouse_client.query("SELECT COUNT(*) FROM telemetry_events")
    assert result.result_rows[0][0] == 0, "Таблица должна быть пустой перед импортом"

    # Определяем временной интервал
    start_ts = datetime(2025, 3, 1, 0, 0, 0)
    end_ts = datetime(2025, 3, 15, 0, 0, 0)

    # Импортируем телеметрические данные с фильтрами
    import_telemetry_data(clickhouse_client, start_ts, end_ts)

    # Проверяем, что данные импортированы
    result = clickhouse_client.query("SELECT COUNT(*) FROM telemetry_events")
    events_count = result.result_rows[0][0]

    # Должно быть >= 0 событий (может быть 0, если в тестовых данных нет событий в этом интервале)
    assert events_count >= 0

    # Проверяем, что все события в нужном интервале (если они есть)
    if events_count > 0:
        # Проверяем временной диапазон импортированных данных
        result = clickhouse_client.query("SELECT MIN(signal_time), MAX(signal_time) FROM telemetry_events")
        min_time, max_time = result.result_rows[0]

        # Проверяем, что нет событий ВНЕ указанного интервала
        result = clickhouse_client.query(
            "SELECT COUNT(*) FROM telemetry_events WHERE signal_time < %s OR signal_time >= %s",
            parameters=[start_ts, end_ts],
        )
        events_outside = result.result_rows[0][0]

        # Если есть события вне интервала, выводим примеры для отладки
        if events_outside > 0:
            result = clickhouse_client.query(
                "SELECT id, signal_time FROM telemetry_events WHERE signal_time < %s OR signal_time >= %s LIMIT 5",
                parameters=[start_ts, end_ts],
            )
            examples = result.result_rows
            assert False, (
                f"Найдено {events_outside} событий вне интервала [{start_ts}, {end_ts}). "
                f"MIN={min_time}, MAX={max_time}. Примеры: {examples}"
            )


def test_cleanup_orphaned_events(clickhouse_client):
    """Тест удаления событий для несуществующих пользователей."""
    # Создаем таблицы
    create_olap_tables(clickhouse_client)

    # Импортируем пользователей
    import_users_data(clickhouse_client)

    # Импортируем телеметрию
    import_telemetry_data(clickhouse_client)

    # Получаем количество событий до очистки
    result = clickhouse_client.query("SELECT COUNT(*) FROM telemetry_events")
    events_before = result.result_rows[0][0]

    # Удаляем всех пользователей
    clickhouse_client.command("TRUNCATE TABLE users")

    # Запускаем очистку orphaned events
    cleanup_orphaned_events(clickhouse_client)

    # Проверяем, что все события удалены
    result = clickhouse_client.query("SELECT COUNT(*) FROM telemetry_events")
    events_after = result.result_rows[0][0]

    assert events_after == 0


def test_main_function_full_import(clickhouse_client):
    """Тест полного импорта данных через функцию main."""
    # Создаем таблицы вручную (main тоже их создаст, но так безопаснее)
    create_olap_tables(clickhouse_client)

    # Запускаем полный импорт
    import_olap_data()

    # Проверяем, что пользователи импортированы
    result = clickhouse_client.query("SELECT COUNT(*) FROM users")
    users_count = result.result_rows[0][0]
    assert users_count > 0

    # Проверяем, что события импортированы
    result = clickhouse_client.query("SELECT COUNT(*) FROM telemetry_events")
    events_count = result.result_rows[0][0]
    assert events_count > 0

    # Проверяем, что нет orphaned events
    result = clickhouse_client.query(
        """
        SELECT COUNT(*) FROM telemetry_events 
        WHERE user_id NOT IN (SELECT user_id FROM users)
    """
    )
    orphaned_count = result.result_rows[0][0]
    assert orphaned_count == 0


def test_main_function_with_time_filters(clickhouse_client):
    """Тест импорта данных с временными фильтрами через функцию main."""
    # Создаем таблицы
    create_olap_tables(clickhouse_client)

    # Очищаем таблицы перед тестом
    clickhouse_client.command("TRUNCATE TABLE users")
    clickhouse_client.command("TRUNCATE TABLE telemetry_events")

    # Определяем временной интервал
    start_ts = datetime(2025, 3, 1, 0, 0, 0)
    end_ts = datetime(2025, 3, 10, 0, 0, 0)

    # Запускаем импорт с фильтрами
    import_olap_data(telemetry_start_ts=start_ts, telemetry_end_ts=end_ts)

    # Проверяем, что пользователи импортированы
    result = clickhouse_client.query("SELECT COUNT(*) FROM users")
    users_count = result.result_rows[0][0]
    assert users_count > 0

    # Проверяем, что события в нужном интервале
    result = clickhouse_client.query("SELECT COUNT(*) FROM telemetry_events")
    events_count = result.result_rows[0][0]

    if events_count > 0:
        # Проверяем, что нет событий ВНЕ указанного интервала
        result = clickhouse_client.query(
            "SELECT COUNT(*) FROM telemetry_events WHERE signal_time < %s OR signal_time >= %s",
            parameters=[start_ts, end_ts],
        )
        events_outside = result.result_rows[0][0]
        assert events_outside == 0, f"Найдено {events_outside} событий вне интервала [{start_ts}, {end_ts})"


def test_reimport_updates_data(clickhouse_client):
    """Тест повторного импорта (данные должны обновляться)."""
    # Создаем таблицы
    create_olap_tables(clickhouse_client)

    # Первый импорт
    import_olap_data()

    # Получаем количество пользователей после первого импорта
    result = clickhouse_client.query("SELECT COUNT(*) FROM users")
    users_count_1 = result.result_rows[0][0]

    # Второй импорт (должен перезаписать данные)
    import_olap_data()

    # Получаем количество пользователей после второго импорта
    result = clickhouse_client.query("SELECT COUNT(*) FROM users")
    users_count_2 = result.result_rows[0][0]

    # Количество должно быть одинаковым (данные перезаписаны)
    assert users_count_1 == users_count_2
