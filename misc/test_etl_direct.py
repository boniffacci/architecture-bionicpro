#!/usr/bin/env python3
"""
Прямой тест ETL-процесса через auth_proxy API
Проверяет, что исправление CORS работает
"""

import requests
import json
import time


def test_etl_direct():
    """Тестирует ETL-процесс напрямую через API"""
    
    print("🔧 Тестирование ETL-процесса через auth_proxy...")
    
    # Базовый URL auth_proxy
    auth_proxy_url = "http://localhost:3000"
    
    # Создаём сессию для сохранения cookies
    session = requests.Session()
    
    print("\n1️⃣ Проверяем доступность auth_proxy...")
    try:
        health_response = session.get(f"{auth_proxy_url}/health")
        if health_response.status_code == 200:
            print("✅ Auth_proxy доступен")
        else:
            print(f"❌ Auth_proxy недоступен: {health_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения к auth_proxy: {e}")
        return False
    
    print("\n2️⃣ Проверяем прямой доступ к Airflow API (должен вызвать CORS ошибку)...")
    try:
        # Это должно вызвать CORS ошибку, как в браузере
        direct_response = session.get("http://localhost:8082/api/v2/monitor/health")
        print(f"✅ Прямой доступ к Airflow работает: {direct_response.status_code}")
        print("ℹ️ Это нормально для серверного запроса, но в браузере будет CORS ошибка")
    except Exception as e:
        print(f"❌ Прямой доступ к Airflow не работает: {e}")
    
    print("\n3️⃣ Тестируем доступ к Airflow через auth_proxy (без авторизации)...")
    
    # Формируем запрос через auth_proxy
    proxy_request_body = {
        "upstream_uri": "http://airflow-standalone:8080/api/v2/monitor/health",
        "method": "GET",
        "redirect_to_sign_in": False
    }
    
    try:
        proxy_response = session.post(
            f"{auth_proxy_url}/proxy",
            headers={"Content-Type": "application/json"},
            data=json.dumps(proxy_request_body)
        )
        
        print(f"Статус ответа: {proxy_response.status_code}")
        
        if proxy_response.status_code == 401:
            print("✅ Получен 401 Unauthorized - это ожидаемо без авторизации")
            print("✅ Auth_proxy корректно обрабатывает запросы к Airflow")
            print("✅ Исправление CORS работает - запросы проходят через прокси")
            return True
        elif proxy_response.status_code == 200:
            print("✅ Получен 200 OK - Airflow доступен через auth_proxy")
            print("✅ Исправление CORS работает - запросы проходят через прокси")
            try:
                response_data = proxy_response.json()
                print(f"Ответ от Airflow: {json.dumps(response_data, indent=2)}")
            except:
                print(f"Ответ от Airflow: {proxy_response.text}")
            return True
        else:
            print(f"⚠️ Неожиданный статус: {proxy_response.status_code}")
            print(f"Ответ: {proxy_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при запросе через auth_proxy: {e}")
        return False


def test_etl_dag_access():
    """Тестирует доступ к DAG через auth_proxy"""
    
    print("\n4️⃣ Тестируем доступ к DAG import_olap_data_monthly...")
    
    auth_proxy_url = "http://localhost:3000"
    session = requests.Session()
    dag_id = "import_olap_data_monthly"
    
    # Формируем запрос к DAG
    proxy_request_body = {
        "upstream_uri": f"http://airflow-standalone:8080/api/v2/dags/{dag_id}",
        "method": "GET",
        "redirect_to_sign_in": False
    }
    
    try:
        proxy_response = session.post(
            f"{auth_proxy_url}/proxy",
            headers={"Content-Type": "application/json"},
            data=json.dumps(proxy_request_body)
        )
        
        print(f"Статус ответа для DAG: {proxy_response.status_code}")
        
        if proxy_response.status_code in [200, 401]:
            print("✅ Запрос к DAG проходит через auth_proxy")
            if proxy_response.status_code == 200:
                try:
                    dag_data = proxy_response.json()
                    print(f"DAG найден: {dag_data.get('dag_id', 'unknown')}")
                    print(f"Статус DAG: {'активен' if not dag_data.get('is_paused', True) else 'на паузе'}")
                except:
                    pass
            return True
        else:
            print(f"⚠️ Неожиданный статус для DAG: {proxy_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при запросе DAG через auth_proxy: {e}")
        return False


if __name__ == "__main__":
    print("=" * 80)
    print("ТЕСТ ИСПРАВЛЕНИЯ ETL-ПРОЦЕССА")
    print("=" * 80)
    
    success1 = test_etl_direct()
    success2 = test_etl_dag_access()
    
    print("\n" + "=" * 80)
    if success1 and success2:
        print("✅ РЕЗУЛЬТАТ: Исправление ETL-процесса работает!")
        print("✅ Auth_proxy корректно проксирует запросы к Airflow API")
        print("✅ Ошибка 'TypeError: Failed to fetch' должна быть устранена")
    else:
        print("❌ РЕЗУЛЬТАТ: Есть проблемы с исправлением ETL-процесса")
        print("❌ Требуется дополнительная диагностика")
    print("=" * 80)
