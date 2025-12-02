#!/usr/bin/env python3
"""
Тест для проверки структуры JWT токенов после изменений в Keycloak
"""

import requests
import json
import jwt
import time


def get_token_from_keycloak():
    """Получает токен от Keycloak для prosthetic1"""
    
    print("Получение токена от Keycloak...")
    
    # Параметры для получения токена
    token_url = "http://localhost:8080/realms/reports-realm/protocol/openid-connect/token"
    
    data = {
        "grant_type": "password",
        "client_id": "reports-frontend",
        "username": "prosthetic1",
        "password": "prosthetic123"
    }
    
    try:
        response = requests.post(token_url, data=data, timeout=10)
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            print("✅ Токен получен успешно")
            return access_token
        else:
            print(f"❌ Ошибка получения токена: {response.status_code}")
            print(f"Ответ: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка при запросе токена: {e}")
        return None


def decode_jwt_token(token):
    """Декодирует JWT токен без проверки подписи для анализа структуры"""
    
    print("\nАнализ структуры JWT токена...")
    
    try:
        # Декодируем без проверки подписи для анализа
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        print("✅ Токен декодирован успешно")
        print("\nСтруктура токена:")
        print(json.dumps(decoded, indent=2, ensure_ascii=False))
        
        # Проверяем наличие нужных полей
        print("\n" + "=" * 50)
        print("АНАЛИЗ ПОЛЕЙ:")
        print("=" * 50)
        
        # Проверяем realm_roles
        if "realm_roles" in decoded:
            print(f"✅ realm_roles найдено: {decoded['realm_roles']}")
        else:
            print("❌ realm_roles НЕ найдено")
        
        # Проверяем старое поле realm_access
        if "realm_access" in decoded:
            print(f"⚠️ realm_access всё ещё присутствует: {decoded['realm_access']}")
        else:
            print("✅ realm_access отсутствует (как и должно быть)")
        
        # Проверяем другие важные поля
        important_fields = ["sub", "preferred_username", "email", "external_uuid"]
        for field in important_fields:
            if field in decoded:
                print(f"✅ {field}: {decoded[field]}")
            else:
                print(f"❌ {field}: НЕ найдено")
        
        return decoded
        
    except Exception as e:
        print(f"❌ Ошибка декодирования токена: {e}")
        return None


def test_reports_api_with_token(token):
    """Тестирует reports_api с новым токеном"""
    
    print("\n" + "=" * 50)
    print("ТЕСТ REPORTS_API:")
    print("=" * 50)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(
            "http://localhost:3003/reports",
            json={"schema": "default"},
            headers=headers,
            timeout=10
        )
        
        print(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Reports API работает с новой структурой JWT")
            data = response.json()
            print(f"Пользователь: {data.get('user_name', 'unknown')}")
            print(f"Email: {data.get('user_email', 'unknown')}")
        elif response.status_code == 403:
            print("❌ Ошибка 403: Нет прав доступа")
            print("Это означает, что роли не читаются из нового поля realm_roles")
            print(f"Ответ: {response.text}")
        else:
            print(f"⚠️ Неожиданный статус: {response.status_code}")
            print(f"Ответ: {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании reports_api: {e}")


if __name__ == "__main__":
    print("=" * 80)
    print("ТЕСТ СТРУКТУРЫ JWT ПОСЛЕ ИЗМЕНЕНИЙ В KEYCLOAK")
    print("=" * 80)
    
    # Ждём готовности Keycloak
    print("Ожидание готовности Keycloak...")
    time.sleep(5)
    
    # Получаем токен
    token = get_token_from_keycloak()
    
    if token:
        # Анализируем структуру
        decoded = decode_jwt_token(token)
        
        # Тестируем API
        test_reports_api_with_token(token)
    
    print("\n" + "=" * 80)
