"""
Интеграционный тест для проверки доступа к MinIO через nginx-proxy с JWT-валидацией.

Тест проверяет:
1. Запись файлов в MinIO (reports/default/... и reports/debezium/...)
2. Доступ к файлам через nginx-proxy с JWT-токеном
3. Проверку прав доступа (пользователь может читать только свои файлы)
"""

import pytest
import requests
import json
import jwt
import time
import io
from datetime import datetime, timedelta
from minio import Minio
from minio.error import S3Error


# JWT токен для тестирования (customer3)
TEST_JWT_PAYLOAD = {
    "exp": int(time.time() + 3600),  # Текущее время + 1 час
    "iat": int(time.time()),
    "auth_time": int(time.time()),
    "jti": "test-jti-12345",
    "iss": "http://localhost:8080/realms/reports-realm",
    "sub": "44e964c6-b928-4f01-abf0-bc14867929c0",  # customer3 UUID
    "typ": "Bearer",
    "azp": "reports-frontend",
    "sid": "test-session-id",
    "acr": "1",
    "allowed-origins": ["*", "http://localhost:3000", "http://localhost:5173"],
    "realm_access": {"roles": ["customers", "prosthetic_users", "users"]},
    "scope": "openid profile email",
    "realm_roles": ["customers", "prosthetic_users", "users"],
    "email_verified": False,
    "name": "Customer Customer",
    "external_uuid": "4f1228fa-89ff-49eb-a27b-876ff84359a2",
    "preferred_username": "customer3",
    "given_name": "Customer",
    "family_name": "Customer",
    "email": "customer3@bionicpro.zm",
    "policy": "prosthetic-user-policy"
}

# Секретный ключ для подписи JWT (должен совпадать с Keycloak, но для теста используем тестовый)
JWT_SECRET = "test-secret-key-for-testing-only"


def create_test_jwt(payload: dict) -> str:
    """Создаёт тестовый JWT токен."""
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


@pytest.fixture(scope="module")
def minio_client():
    """Создаёт клиент MinIO для прямого доступа."""
    client = Minio(
        "localhost:9000",
        access_key="minio_user",
        secret_key="minio_password",
        secure=False
    )
    return client


@pytest.fixture(scope="module")
def test_user_uuid():
    """UUID тестового пользователя (customer3) - используем external_uuid из JWT."""
    return "4f1228fa-89ff-49eb-a27b-876ff84359a2"  # external_uuid из JWT


@pytest.fixture(scope="module")
def other_user_uuid():
    """UUID другого пользователя для проверки запрета доступа."""
    return "54885c9b-6eea-48f7-89f9-353ad8273e95"  # prosthetic1


def test_minio_nginx_proxy_access(minio_client, test_user_uuid, other_user_uuid):
    """
    Тест проверяет доступ к MinIO через nginx-proxy с JWT-валидацией.
    
    Шаги:
    1. Записываем тестовые файлы в MinIO для test_user и other_user
    2. Пытаемся получить доступ к своему файлу через nginx-proxy (должно работать)
    3. Пытаемся получить доступ к чужому файлу через nginx-proxy (должна быть ошибка 403)
    """
    
    print("\n" + "="*80)
    print("Тест доступа к MinIO через nginx-proxy с JWT-валидацией")
    print("="*80)
    
    # Шаг 1: Записываем тестовые файлы в MinIO
    print("\n1. Записываем тестовые файлы в MinIO...")
    
    test_data_own = {
        "user_name": "Customer Customer",
        "user_email": "customer3@bionicpro.zm",
        "total_events": 100,
        "total_duration": 5000,
        "prosthesis_stats": []
    }
    
    test_data_other = {
        "user_name": "Prosthetic One",
        "user_email": "prosthetic1@example.com",
        "total_events": 50,
        "total_duration": 2500,
        "prosthesis_stats": []
    }
    
    # Записываем файл для test_user (default schema)
    own_file_path_default = f"default/{test_user_uuid}/test_report.json"
    own_data_bytes = json.dumps(test_data_own).encode('utf-8')
    minio_client.put_object(
        "reports",
        own_file_path_default,
        data=io.BytesIO(own_data_bytes),
        length=len(own_data_bytes),
        content_type="application/json"
    )
    print(f"   ✓ Записан файл: reports/{own_file_path_default}")
    
    # Записываем файл для test_user (debezium schema)
    own_file_path_debezium = f"debezium/{test_user_uuid}/test_report.json"
    minio_client.put_object(
        "reports",
        own_file_path_debezium,
        data=io.BytesIO(own_data_bytes),
        length=len(own_data_bytes),
        content_type="application/json"
    )
    print(f"   ✓ Записан файл: reports/{own_file_path_debezium}")
    
    # Записываем файл для other_user (default schema)
    other_file_path_default = f"default/{other_user_uuid}/test_report.json"
    other_data_bytes = json.dumps(test_data_other).encode('utf-8')
    minio_client.put_object(
        "reports",
        other_file_path_default,
        data=io.BytesIO(other_data_bytes),
        length=len(other_data_bytes),
        content_type="application/json"
    )
    print(f"   ✓ Записан файл: reports/{other_file_path_default}")
    
    # Шаг 2: Создаём JWT токен
    print("\n2. Создаём JWT токен для customer3...")
    token = create_test_jwt(TEST_JWT_PAYLOAD)
    print(f"   ✓ JWT токен создан (длина: {len(token)} символов)")
    
    # Шаг 3: Пытаемся получить доступ к своему файлу (default schema)
    print(f"\n3. Пытаемся получить доступ к своему файлу (default schema)...")
    print(f"   URL: http://localhost:9002/reports/{own_file_path_default}")
    
    response_own_default = requests.get(
        f"http://localhost:9002/reports/{own_file_path_default}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"   Статус: {response_own_default.status_code}")
    if response_own_default.status_code == 200:
        print("   ✓ Доступ к своему файлу (default) разрешён")
        data = response_own_default.json()
        assert data["user_email"] == "customer3@bionicpro.zm"
    else:
        print(f"   ✗ Ошибка доступа: {response_own_default.text}")
        pytest.fail(f"Не удалось получить доступ к своему файлу (default): {response_own_default.status_code}")
    
    # Шаг 4: Пытаемся получить доступ к своему файлу (debezium schema)
    print(f"\n4. Пытаемся получить доступ к своему файлу (debezium schema)...")
    print(f"   URL: http://localhost:9002/reports/{own_file_path_debezium}")
    
    response_own_debezium = requests.get(
        f"http://localhost:9002/reports/{own_file_path_debezium}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"   Статус: {response_own_debezium.status_code}")
    if response_own_debezium.status_code == 200:
        print("   ✓ Доступ к своему файлу (debezium) разрешён")
        data = response_own_debezium.json()
        assert data["user_email"] == "customer3@bionicpro.zm"
    else:
        print(f"   ✗ Ошибка доступа: {response_own_debezium.text}")
        pytest.fail(f"Не удалось получить доступ к своему файлу (debezium): {response_own_debezium.status_code}")
    
    # Шаг 5: Пытаемся получить доступ к чужому файлу (должна быть ошибка 403)
    print(f"\n5. Пытаемся получить доступ к чужому файлу (должна быть ошибка 403)...")
    print(f"   URL: http://localhost:9002/reports/{other_file_path_default}")
    
    response_other = requests.get(
        f"http://localhost:9002/reports/{other_file_path_default}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"   Статус: {response_other.status_code}")
    if response_other.status_code == 403:
        print("   ✓ Доступ к чужому файлу запрещён (403)")
        error_data = response_other.json()
        assert "Access denied" in error_data.get("error", "")
    else:
        print(f"   ✗ Неожиданный статус: {response_other.status_code}")
        print(f"   Ответ: {response_other.text}")
        pytest.fail(f"Ожидался статус 403, получен {response_other.status_code}")
    
    # Шаг 6: Пытаемся получить доступ без JWT токена (должна быть ошибка 401)
    print(f"\n6. Пытаемся получить доступ без JWT токена (должна быть ошибка 401)...")
    
    response_no_token = requests.get(
        f"http://localhost:9002/reports/{own_file_path_default}"
    )
    
    print(f"   Статус: {response_no_token.status_code}")
    if response_no_token.status_code == 401:
        print("   ✓ Доступ без токена запрещён (401)")
    else:
        print(f"   ✗ Неожиданный статус: {response_no_token.status_code}")
        pytest.fail(f"Ожидался статус 401, получен {response_no_token.status_code}")
    
    print("\n" + "="*80)
    print("✓ Тест завершён успешно!")
    print("="*80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
