"""Тесты для эндпоинта /reports с JWT-аутентификацией в reports_api."""

import pytest
import requests
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from minio import Minio
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path для импорта из dags/
sys.path.insert(0, str(Path(__file__).parent.parent))

from reports_api.main import app, init_minio, get_minio_client
from dags.import_olap_data import import_olap_data as import_main, get_clickhouse_client


# Keycloak-конфигурация для получения токенов
KEYCLOAK_URL = "http://localhost:8080"
REALM = "reports-realm"
CLIENT_ID = "reports-frontend"


def get_access_token(username: str, password: str) -> str:
    """
    Получает JWT-токен из Keycloak для указанного пользователя.
    
    Args:
        username: Имя пользователя
        password: Пароль пользователя
        
    Returns:
        str: JWT access token
    """
    token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"
    
    data = {
        "grant_type": "password",
        "client_id": CLIENT_ID,
        "username": username,
        "password": password,
    }
    
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def setup_olap_data():
    """Фикстура для подготовки данных в ClickHouse перед тестами."""
    # Импортируем данные в ClickHouse
    import_main()
    yield


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


@pytest.fixture
def prosthetic1_token():
    """Фикстура для получения JWT-токена пользователя prosthetic1."""
    return get_access_token("prosthetic1", "prosthetic123")


@pytest.fixture
def prosthetic2_token():
    """Фикстура для получения JWT-токена пользователя prosthetic2."""
    return get_access_token("prosthetic2", "prosthetic123")


@pytest.fixture
def admin_token():
    """Фикстура для получения JWT-токена администратора."""
    try:
        return get_access_token("admin", "admin123")
    except Exception:
        pytest.skip("Администратор недоступен в Keycloak")


def test_reports_endpoint_without_auth(client: TestClient):
    """Тест что эндпоинт /reports требует аутентификацию."""
    response = client.post("/reports", json={})
    # Должна быть ошибка 401 (Unauthorized)
    assert response.status_code == 401


def test_reports_endpoint_with_invalid_token(client: TestClient):
    """Тест что эндпоинт /reports отклоняет невалидный токен."""
    headers = {"Authorization": "Bearer invalid_token_here"}
    response = client.post("/reports", json={}, headers=headers)
    # Должна быть ошибка 401 (Unauthorized)
    assert response.status_code == 401


def test_reports_for_prosthetic_user_default_schema(
    client: TestClient, 
    setup_olap_data, 
    prosthetic1_token: str
):
    """Тест генерации отчета для prosthetic1 из default-схемы."""
    headers = {"Authorization": f"Bearer {prosthetic1_token}"}
    
    # Запрашиваем отчет без указания user_uuid (берётся из JWT)
    response = client.post("/reports", json={"schema": "default"}, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем структуру ответа
    assert "user_name" in data
    assert "user_email" in data
    assert "total_events" in data
    assert "total_duration" in data
    assert "prosthesis_stats" in data
    
    # Проверяем, что это данные prosthetic1
    assert data["user_email"] == "prosthetic1@example.com"
    assert data["user_name"] == "Prosthetic One"
    
    # Проверяем типы данных
    assert isinstance(data["total_events"], int)
    assert isinstance(data["total_duration"], int)
    assert isinstance(data["prosthesis_stats"], list)


def test_reports_for_prosthetic_user_debezium_schema(
    client: TestClient, 
    setup_olap_data, 
    prosthetic1_token: str
):
    """Тест генерации отчета для prosthetic1 из debezium-схемы."""
    headers = {"Authorization": f"Bearer {prosthetic1_token}"}
    
    # Запрашиваем отчет из debezium-схемы
    response = client.post("/reports", json={"schema": "debezium"}, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем структуру ответа
    assert "user_name" in data
    assert "user_email" in data
    assert "total_events" in data
    
    # Проверяем, что это данные prosthetic1
    assert data["user_email"] == "prosthetic1@example.com"


def test_reports_caching_default_schema(
    client: TestClient, 
    setup_olap_data, 
    prosthetic2_token: str
):
    """Тест генерации отчетов в default-схеме (кэширование теперь на фронтенде)."""
    headers = {"Authorization": f"Bearer {prosthetic2_token}"}
    
    # Очищаем кэш для prosthetic2
    minio = get_minio_client()
    bucket_name = "reports"
    user_uuid = "7f7861be-8810-4c0c-bdd0-893b6a91aec5"  # UUID prosthetic2
    try:
        objects = minio.list_objects(bucket_name, prefix=f"default/{user_uuid}/", recursive=True)
        for obj in objects:
            minio.remove_object(bucket_name, obj.object_name)
    except Exception:
        pass
    
    # Первый запрос - генерируем отчет
    response1 = client.post("/reports", json={"schema": "default"}, headers=headers)
    assert response1.status_code == 200
    data1 = response1.json()
    
    # Проверяем, что файл появился в MinIO
    file_name = f"default/{user_uuid}/none__2025-11-01T00-00-00.json"
    try:
        obj = minio.get_object(bucket_name, file_name)
        obj.close()
        obj.release_conn()
        cache_exists = True
    except Exception:
        cache_exists = False
    
    assert cache_exists, f"Отчет должен быть сохранен в MinIO: {file_name}"
    
    # Второй запрос - генерируем отчет заново (reports_api больше не проверяет кэш)
    response2 = client.post("/reports", json={"schema": "default"}, headers=headers)
    assert response2.status_code == 200
    data2 = response2.json()
    
    # Проверяем, что данные идентичны
    assert data1 == data2


def test_reports_caching_debezium_schema(
    client: TestClient, 
    setup_olap_data, 
    prosthetic2_token: str
):
    """Тест генерации отчетов в debezium-схеме (кэширование теперь на фронтенде)."""
    headers = {"Authorization": f"Bearer {prosthetic2_token}"}
    
    # Очищаем кэш для prosthetic2
    minio = get_minio_client()
    bucket_name = "reports"
    user_uuid = "7f7861be-8810-4c0c-bdd0-893b6a91aec5"  # UUID prosthetic2
    try:
        objects = minio.list_objects(bucket_name, prefix=f"debezium/{user_uuid}/", recursive=True)
        for obj in objects:
            minio.remove_object(bucket_name, obj.object_name)
    except Exception:
        pass
    
    # Первый запрос - генерируем отчет
    response1 = client.post("/reports", json={"schema": "debezium"}, headers=headers)
    assert response1.status_code == 200
    data1 = response1.json()
    
    # Проверяем, что файл появился в MinIO
    file_name = f"debezium/{user_uuid}/none__2025-11-01T00-00-00.json"
    try:
        obj = minio.get_object(bucket_name, file_name)
        obj.close()
        obj.release_conn()
        cache_exists = True
    except Exception:
        cache_exists = False
    
    assert cache_exists, f"Отчет должен быть сохранен в MinIO: {file_name}"
    
    # Второй запрос - генерируем отчет заново
    response2 = client.post("/reports", json={"schema": "debezium"}, headers=headers)
    assert response2.status_code == 200
    data2 = response2.json()
    
    # Проверяем, что данные идентичны
    assert data1 == data2


def test_reports_with_time_filters(
    client: TestClient, 
    setup_olap_data, 
    prosthetic1_token: str
):
    """Тест генерации отчета с временными фильтрами."""
    headers = {"Authorization": f"Bearer {prosthetic1_token}"}
    
    # Запрашиваем отчет с временными фильтрами
    response = client.post(
        "/reports",
        json={
            "schema": "default",
            "start_ts": "2025-03-01T00:00:00",
            "end_ts": "2025-03-31T23:59:59"
        },
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что отчет сгенерирован
    assert "total_events" in data
    assert data["total_events"] >= 0


def test_admin_can_view_other_user_report(
    client: TestClient, 
    setup_olap_data, 
    admin_token: str
):
    """Тест что администратор может просматривать отчеты других пользователей."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # UUID prosthetic1
    prosthetic1_uuid = "54885c9b-6eea-48f7-89f9-353ad8273e95"
    
    # Запрашиваем отчет для prosthetic1 от имени администратора
    response = client.post(
        "/reports",
        json={"user_uuid": prosthetic1_uuid, "schema": "default"},
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что это данные prosthetic1
    assert data["user_email"] == "prosthetic1@example.com"


def test_prosthetic_user_cannot_view_other_user_report(
    client: TestClient, 
    setup_olap_data, 
    prosthetic1_token: str
):
    """Тест что prosthetic_user не может просматривать отчеты других пользователей."""
    headers = {"Authorization": f"Bearer {prosthetic1_token}"}
    
    # UUID prosthetic2
    prosthetic2_uuid = "7f7861be-8810-4c0c-bdd0-893b6a91aec5"
    
    # Пытаемся запросить отчет для prosthetic2 от имени prosthetic1
    response = client.post(
        "/reports",
        json={"user_uuid": prosthetic2_uuid, "schema": "default"},
        headers=headers
    )
    
    # Должна быть ошибка 403 (Forbidden)
    assert response.status_code == 403
    assert "нет прав" in response.json()["detail"].lower()


def test_prosthetic_user_can_view_own_report_with_explicit_uuid(
    client: TestClient, 
    setup_olap_data, 
    prosthetic1_token: str
):
    """Тест что prosthetic_user может просматривать свой отчет, указав свой UUID явно."""
    headers = {"Authorization": f"Bearer {prosthetic1_token}"}
    
    # UUID prosthetic1 (тот же, что и в JWT)
    prosthetic1_uuid = "54885c9b-6eea-48f7-89f9-353ad8273e95"
    
    # Запрашиваем отчет для себя, указав свой UUID явно
    response = client.post(
        "/reports",
        json={"user_uuid": prosthetic1_uuid, "schema": "default"},
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что это данные prosthetic1
    assert data["user_email"] == "prosthetic1@example.com"


def test_admin_can_view_multiple_users_reports(
    client: TestClient, 
    setup_olap_data, 
    admin_token: str
):
    """Тест что администратор может просматривать отчеты разных пользователей."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # UUID разных пользователей
    prosthetic1_uuid = "54885c9b-6eea-48f7-89f9-353ad8273e95"
    prosthetic2_uuid = "7f7861be-8810-4c0c-bdd0-893b6a91aec5"
    
    # Запрашиваем отчет для prosthetic1
    response1 = client.post(
        "/reports",
        json={"user_uuid": prosthetic1_uuid, "schema": "default"},
        headers=headers
    )
    
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["user_email"] == "prosthetic1@example.com"
    
    # Запрашиваем отчет для prosthetic2
    response2 = client.post(
        "/reports",
        json={"user_uuid": prosthetic2_uuid, "schema": "default"},
        headers=headers
    )
    
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["user_email"] == "prosthetic2@example.com"
    
    # Проверяем, что отчеты разные
    assert data1["user_email"] != data2["user_email"]


def test_custom_uuid_overrides_jwt_sub(
    client: TestClient, 
    setup_olap_data, 
    admin_token: str
):
    """Тест что кастомный user_uuid переопределяет sub из JWT."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # UUID prosthetic1 (не администратора)
    prosthetic1_uuid = "54885c9b-6eea-48f7-89f9-353ad8273e95"
    
    # Администратор запрашивает отчет для prosthetic1
    response = client.post(
        "/reports",
        json={"user_uuid": prosthetic1_uuid, "schema": "default"},
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что получили данные prosthetic1, а не администратора
    assert data["user_email"] == "prosthetic1@example.com"
    # Убеждаемся, что это не данные администратора
    assert data["user_email"] != "admin@example.com"


def test_invalid_uuid_format_handling(
    client: TestClient, 
    setup_olap_data, 
    admin_token: str
):
    """Тест обработки невалидного формата UUID."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Невалидный UUID
    invalid_uuid = "invalid-uuid-format"
    
    # Запрашиваем отчет с невалидным UUID
    response = client.post(
        "/reports",
        json={"user_uuid": invalid_uuid, "schema": "default"},
        headers=headers
    )
    
    # Может быть 400 (Bad Request) или 404 (Not Found), в зависимости от реализации
    # Главное, что не 200 и не 500
    assert response.status_code in [400, 404, 422]


def test_nonexistent_uuid_handling(
    client: TestClient, 
    setup_olap_data, 
    admin_token: str
):
    """Тест обработки несуществующего UUID."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Валидный формат UUID, но несуществующий пользователь
    nonexistent_uuid = "00000000-0000-0000-0000-000000000000"
    
    # Запрашиваем отчет для несуществующего пользователя
    response = client.post(
        "/reports",
        json={"user_uuid": nonexistent_uuid, "schema": "default"},
        headers=headers
    )
    
    # Должен вернуться отчет с пустыми данными или 404
    # В текущей реализации возвращается пустой отчет
    assert response.status_code in [200, 404]
    
    if response.status_code == 200:
        data = response.json()
        # Проверяем, что данные пустые или содержат информацию об отсутствии пользователя
        assert data["total_events"] == 0 or "user_name" in data


def test_reports_prosthesis_stats_structure(
    client: TestClient, 
    setup_olap_data, 
    prosthetic1_token: str
):
    """Тест структуры статистики по протезам."""
    headers = {"Authorization": f"Bearer {prosthetic1_token}"}
    
    # Запрашиваем отчет
    response = client.post("/reports", json={"schema": "default"}, headers=headers)
    
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


def test_reports_both_schemas_return_same_data(
    client: TestClient, 
    setup_olap_data, 
    prosthetic1_token: str
):
    """Тест что default и debezium схемы возвращают одинаковые данные."""
    headers = {"Authorization": f"Bearer {prosthetic1_token}"}
    
    # Запрашиваем отчет из default-схемы
    response_default = client.post("/reports", json={"schema": "default"}, headers=headers)
    assert response_default.status_code == 200
    data_default = response_default.json()
    
    # Запрашиваем отчет из debezium-схемы
    response_debezium = client.post("/reports", json={"schema": "debezium"}, headers=headers)
    assert response_debezium.status_code == 200
    data_debezium = response_debezium.json()
    
    # Проверяем, что основные метрики совпадают
    assert data_default["user_email"] == data_debezium["user_email"]
    assert data_default["user_name"] == data_debezium["user_name"]
    # Количество событий может немного отличаться из-за времени репликации
    # но должно быть примерно одинаковым
    assert abs(data_default["total_events"] - data_debezium["total_events"]) <= 100
