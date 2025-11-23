"""Тесты для эндпоинта /report в reports_api."""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from minio import Minio
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path для импорта из dags/
sys.path.insert(0, str(Path(__file__).parent.parent))

from reports_api.main import app, init_minio, get_minio_client
from dags.import_olap_data import import_olap_data as import_main, get_clickhouse_client


@pytest.fixture(scope="module")
def setup_olap_data():
    """Фикстура для подготовки данных в ClickHouse перед тестами."""
    # Импортируем данные в ClickHouse
    import_main()
    yield
    # После тестов можно очистить данные, но оставим для других тестов


@pytest.fixture(scope="module")
def setup_minio():
    """Фикстура для инициализации MinIO перед тестами."""
    # Инициализируем MinIO
    init_minio()
    yield
    # После тестов очищаем бакет reports
    try:
        minio = get_minio_client()
        bucket_name = "reports"
        # Удаляем все объекты из бакета
        objects = minio.list_objects(bucket_name, recursive=True)
        for obj in objects:
            minio.remove_object(bucket_name, obj.object_name)
    except Exception as e:
        print(f"Ошибка при очистке MinIO: {e}")


@pytest.fixture
def client(setup_minio):
    """Фикстура для тестового клиента FastAPI."""
    return TestClient(app)


def test_report_endpoint_exists(client: TestClient):
    """Тест что эндпоинт /report существует."""
    # Пробуем вызвать эндпоинт с некорректными данными
    response = client.post("/report", json={})
    # Должна быть ошибка валидации (422), а не 404
    assert response.status_code == 422


def test_report_for_existing_user(client: TestClient, setup_olap_data):
    """Тест генерации отчета для существующего пользователя."""
    # Получаем ID первого пользователя из ClickHouse
    ch_client = get_clickhouse_client()
    result = ch_client.query("SELECT user_id FROM users LIMIT 1")

    if not result.result_rows:
        pytest.skip("Нет пользователей в OLAP БД")

    user_id = result.result_rows[0][0]

    # Запрашиваем отчет
    response = client.post("/report", json={"user_id": user_id})

    assert response.status_code == 200
    data = response.json()

    # Проверяем структуру ответа
    assert "user_name" in data
    assert "user_email" in data
    assert "total_events" in data
    assert "total_duration" in data
    assert "prosthesis_stats" in data

    # Проверяем типы данных
    assert isinstance(data["user_name"], str)
    assert isinstance(data["user_email"], str)
    assert isinstance(data["total_events"], int)
    assert isinstance(data["total_duration"], int)
    assert isinstance(data["prosthesis_stats"], list)


def test_report_for_nonexistent_user(client: TestClient, setup_olap_data):
    """Тест генерации отчета для несуществующего пользователя."""
    # Используем заведомо несуществующий ID
    response = client.post("/report", json={"user_id": 999999})

    # Должна быть ошибка 404
    assert response.status_code == 404
    assert "не найден" in response.json()["detail"]


def test_report_with_time_filters(client: TestClient, setup_olap_data):
    """Тест генерации отчета с временными фильтрами."""
    # Получаем ID пользователя с событиями
    ch_client = get_clickhouse_client()
    result = ch_client.query(
        """
        SELECT user_id 
        FROM telemetry_events 
        GROUP BY user_id 
        HAVING COUNT(*) > 0 
        LIMIT 1
    """
    )

    if not result.result_rows:
        pytest.skip("Нет событий в OLAP БД")

    user_id = result.result_rows[0][0]

    # Запрашиваем отчет с временными фильтрами
    response = client.post(
        "/report", json={"user_id": user_id, "start_ts": "2025-03-01T00:00:00", "end_ts": "2025-03-31T23:59:59"}
    )

    assert response.status_code == 200
    data = response.json()

    # Проверяем, что отчет сгенерирован
    assert "total_events" in data
    assert data["total_events"] >= 0


def test_report_prosthesis_stats_structure(client: TestClient, setup_olap_data):
    """Тест структуры статистики по протезам."""
    # Получаем ID пользователя с событиями
    ch_client = get_clickhouse_client()
    result = ch_client.query(
        """
        SELECT user_id 
        FROM telemetry_events 
        GROUP BY user_id 
        HAVING COUNT(*) > 0 
        LIMIT 1
    """
    )

    if not result.result_rows:
        pytest.skip("Нет событий в OLAP БД")

    user_id = result.result_rows[0][0]

    # Запрашиваем отчет
    response = client.post("/report", json={"user_id": user_id})

    assert response.status_code == 200
    data = response.json()

    # Если есть события, должна быть статистика по протезам
    if data["total_events"] > 0:
        assert len(data["prosthesis_stats"]) > 0

        # Проверяем структуру первой записи
        first_stat = data["prosthesis_stats"][0]
        assert "prosthesis_type" in first_stat
        assert "events_count" in first_stat
        assert "total_duration" in first_stat
        assert "avg_amplitude" in first_stat
        assert "avg_frequency" in first_stat

        # Проверяем типы данных
        assert isinstance(first_stat["prosthesis_type"], str)
        assert isinstance(first_stat["events_count"], int)
        assert isinstance(first_stat["total_duration"], int)
        assert isinstance(first_stat["avg_amplitude"], (int, float))
        assert isinstance(first_stat["avg_frequency"], (int, float))

        # Проверяем, что значения положительные
        assert first_stat["events_count"] > 0
        assert first_stat["total_duration"] >= 0
        assert first_stat["avg_amplitude"] >= 0
        assert first_stat["avg_frequency"] >= 0


def test_report_user_without_events(client: TestClient, setup_olap_data):
    """Тест генерации отчета для пользователя без событий."""
    # Получаем ID пользователя без событий
    ch_client = get_clickhouse_client()
    result = ch_client.query(
        """
        SELECT user_id 
        FROM users 
        WHERE user_id NOT IN (SELECT DISTINCT user_id FROM telemetry_events)
        LIMIT 1
    """
    )

    if not result.result_rows:
        pytest.skip("Все пользователи имеют события")

    user_id = result.result_rows[0][0]

    # Запрашиваем отчет
    response = client.post("/report", json={"user_id": user_id})

    assert response.status_code == 200
    data = response.json()

    # Проверяем, что отчет пустой
    assert data["total_events"] == 0
    assert data["total_duration"] == 0
    assert len(data["prosthesis_stats"]) == 0


def test_report_validation_missing_user_id(client: TestClient):
    """Тест валидации запроса без user_id."""
    response = client.post("/report", json={})

    # Должна быть ошибка валидации
    assert response.status_code == 422


def test_report_validation_invalid_dates(client: TestClient, setup_olap_data):
    """Тест валидации запроса с некорректными датами."""
    # Получаем ID пользователя
    ch_client = get_clickhouse_client()
    result = ch_client.query("SELECT user_id FROM users LIMIT 1")

    if not result.result_rows:
        pytest.skip("Нет пользователей в OLAP БД")

    user_id = result.result_rows[0][0]

    # Пробуем отправить некорректную дату
    response = client.post("/report", json={"user_id": user_id, "start_ts": "invalid-date"})

    # Должна быть ошибка валидации
    assert response.status_code == 422


def test_report_total_duration_calculation(client: TestClient, setup_olap_data):
    """Тест корректности расчета общей длительности."""
    # Получаем ID пользователя с событиями
    ch_client = get_clickhouse_client()
    result = ch_client.query(
        """
        SELECT user_id 
        FROM telemetry_events 
        GROUP BY user_id 
        HAVING COUNT(*) > 0 
        LIMIT 1
    """
    )

    if not result.result_rows:
        pytest.skip("Нет событий в OLAP БД")

    user_id = result.result_rows[0][0]

    # Получаем ожидаемую общую длительность напрямую из БД
    expected_result = ch_client.query(
        """
        SELECT SUM(signal_duration) 
        FROM telemetry_events 
        WHERE user_id = {user_id:Int32}
    """,
        parameters={"user_id": user_id},
    )

    expected_duration = int(expected_result.result_rows[0][0] or 0)

    # Запрашиваем отчет
    response = client.post("/report", json={"user_id": user_id})

    assert response.status_code == 200
    data = response.json()

    # Проверяем, что длительность совпадает
    assert data["total_duration"] == expected_duration


def test_report_minio_caching(client: TestClient, setup_olap_data):
    """Тест кеширования отчетов в MinIO."""
    # Получаем ID пользователя с событиями
    ch_client = get_clickhouse_client()
    result = ch_client.query(
        """
        SELECT user_id 
        FROM telemetry_events 
        GROUP BY user_id 
        HAVING COUNT(*) > 0 
        LIMIT 1
    """
    )

    if not result.result_rows:
        pytest.skip("Нет событий в OLAP БД")

    user_id = result.result_rows[0][0]

    # Очищаем кеш для этого пользователя
    minio = get_minio_client()
    bucket_name = "reports"
    try:
        objects = minio.list_objects(bucket_name, prefix=f"{user_id}/", recursive=True)
        for obj in objects:
            minio.remove_object(bucket_name, obj.object_name)
    except Exception:
        pass

    # Первый запрос - генерируем отчет
    response1 = client.post("/report", json={"user_id": user_id})
    assert response1.status_code == 200
    data1 = response1.json()

    # Проверяем, что файл появился в MinIO
    file_name = f"{user_id}/all_time.json"
    try:
        obj = minio.get_object(bucket_name, file_name)
        obj.close()
        obj.release_conn()
        cache_exists = True
    except Exception:
        cache_exists = False

    assert cache_exists, "Отчет должен быть сохранен в MinIO"

    # Второй запрос - должен загрузиться из кеша
    response2 = client.post("/report", json={"user_id": user_id})
    assert response2.status_code == 200
    data2 = response2.json()

    # Проверяем, что данные идентичны
    assert data1 == data2


def test_report_minio_caching_with_dates(client: TestClient, setup_olap_data):
    """Тест кеширования отчетов с временными фильтрами в MinIO."""
    # Получаем ID пользователя с событиями
    ch_client = get_clickhouse_client()
    result = ch_client.query(
        """
        SELECT user_id 
        FROM telemetry_events 
        GROUP BY user_id 
        HAVING COUNT(*) > 0 
        LIMIT 1
    """
    )

    if not result.result_rows:
        pytest.skip("Нет событий в OLAP БД")

    user_id = result.result_rows[0][0]

    # Очищаем кеш для этого пользователя
    minio = get_minio_client()
    bucket_name = "reports"
    try:
        objects = minio.list_objects(bucket_name, prefix=f"{user_id}/", recursive=True)
        for obj in objects:
            minio.remove_object(bucket_name, obj.object_name)
    except Exception:
        pass

    # Запрос с временными фильтрами
    request_data = {"user_id": user_id, "start_ts": "2025-03-01T00:00:00", "end_ts": "2025-03-31T23:59:59"}

    # Первый запрос
    response1 = client.post("/report", json=request_data)
    assert response1.status_code == 200
    data1 = response1.json()

    # Проверяем, что файл с правильным именем появился в MinIO
    file_name = f"{user_id}/2025-03-01T00-00-00__2025-03-31T23-59-59.json"
    try:
        obj = minio.get_object(bucket_name, file_name)
        obj.close()
        obj.release_conn()
        cache_exists = True
    except Exception:
        cache_exists = False

    assert cache_exists, f"Отчет должен быть сохранен в MinIO с именем {file_name}"

    # Второй запрос - должен загрузиться из кеша
    response2 = client.post("/report", json=request_data)
    assert response2.status_code == 200
    data2 = response2.json()

    # Проверяем, что данные идентичны
    assert data1 == data2
