#!/usr/bin/env python3
"""
Простой тест MinIO без OIDC для проверки базовой функциональности
"""

import requests
import json
from minio import Minio


def test_minio_basic():
    """Тестирует базовую функциональность MinIO"""
    
    print("=" * 60)
    print("ПРОСТОЙ ТЕСТ MINIO")
    print("=" * 60)
    
    # Подключение к MinIO
    minio_client = Minio(
        "localhost:9000",
        access_key="minio_user",
        secret_key="minio_password",
        secure=False
    )
    
    bucket_name = "reports"
    
    try:
        # Проверяем, что бакет существует
        if minio_client.bucket_exists(bucket_name):
            print(f"✅ Бакет {bucket_name} существует")
        else:
            print(f"❌ Бакет {bucket_name} не существует")
            return False
        
        # Создаём тестовый файл
        test_file_path = "default/54885c9b-6eea-48f7-89f9-353ad8273e95/test_file.json"
        test_content = json.dumps({
            "user_name": "Test User",
            "user_email": "test@example.com",
            "total_events": 42
        })
        
        # Загружаем файл
        from io import BytesIO
        minio_client.put_object(
            bucket_name,
            test_file_path,
            BytesIO(test_content.encode()),
            len(test_content.encode()),
            content_type="application/json"
        )
        print(f"✅ Файл {test_file_path} загружен")
        
        # Проверяем прямой доступ к файлу
        file_url = f"http://localhost:9000/{bucket_name}/{test_file_path}"
        response = requests.get(file_url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Файл доступен по прямой ссылке: {file_url}")
            print(f"Содержимое: {response.text}")
            return True
        else:
            print(f"❌ Файл недоступен: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def test_jwt_structure():
    """Тестирует структуру JWT токенов"""
    
    print("\n" + "=" * 60)
    print("ТЕСТ СТРУКТУРЫ JWT")
    print("=" * 60)
    
    try:
        # Получаем токен от Keycloak
        token_url = "http://localhost:8080/realms/reports-realm/protocol/openid-connect/token"
        
        data = {
            "grant_type": "password",
            "client_id": "reports-frontend",
            "username": "prosthetic1",
            "password": "prosthetic123"
        }
        
        response = requests.post(token_url, data=data, timeout=10)
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            # Декодируем токен
            import jwt
            decoded = jwt.decode(access_token, options={"verify_signature": False})
            
            print("✅ JWT токен получен и декодирован")
            print(f"Sub: {decoded.get('sub')}")
            print(f"Realm roles: {decoded.get('realm_roles')}")
            print(f"Policy: {decoded.get('policy')}")
            
            # Проверяем наличие нужных полей
            if decoded.get('realm_roles') and decoded.get('sub'):
                print("✅ JWT содержит необходимые поля для авторизации")
                return True
            else:
                print("❌ JWT не содержит необходимые поля")
                return False
        else:
            print(f"❌ Ошибка получения токена: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании JWT: {e}")
        return False


if __name__ == "__main__":
    success1 = test_minio_basic()
    success2 = test_jwt_structure()
    
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ")
    print("=" * 60)
    
    if success1:
        print("✅ MinIO базовая функциональность работает")
    else:
        print("❌ MinIO базовая функциональность НЕ работает")
    
    if success2:
        print("✅ JWT структура корректна")
    else:
        print("❌ JWT структура НЕ корректна")
    
    if success1 and success2:
        print("\n🎉 Базовые компоненты готовы для интеграции!")
    else:
        print("\n💥 Требуется исправление базовых компонентов")
    
    print("=" * 60)
