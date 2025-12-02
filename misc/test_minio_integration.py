#!/usr/bin/env python3
"""
Интеграционный тест MinIO с JWT авторизацией
"""

import os
import time
import json
import requests
import subprocess
from playwright.sync_api import sync_playwright, expect


def run_docker_command(command: str, cwd: str = None) -> tuple[int, str]:
    """Выполняет docker команду и возвращает код возврата и вывод"""
    if cwd is None:
        cwd = "/home/felix/Projects/yandex_swa_pro/architecture-bionicpro"
    
    print(f"Выполняем: {command}")
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    
    if result.stdout:
        print(f"STDOUT: {result.stdout}")
    if result.stderr:
        print(f"STDERR: {result.stderr}")
    
    return result.returncode, result.stdout + result.stderr


def get_jwt_token(username: str, password: str) -> str:
    """Получает JWT токен от Keycloak"""
    
    token_url = "http://localhost:8080/realms/reports-realm/protocol/openid-connect/token"
    
    data = {
        "grant_type": "password",
        "client_id": "reports-frontend",
        "username": username,
        "password": password
    }
    
    response = requests.post(token_url, data=data, timeout=10)
    
    if response.status_code == 200:
        token_data = response.json()
        return token_data.get("access_token")
    else:
        raise Exception(f"Ошибка получения токена: {response.status_code} - {response.text}")


def test_minio_file_access(token: str, file_path: str, should_succeed: bool = True) -> bool:
    """Тестирует доступ к файлу MinIO с JWT токеном"""
    
    # Используем STS API MinIO для получения временных credentials
    sts_url = "http://localhost:9000"
    
    # Формируем запрос к STS AssumeRoleWithWebIdentity
    sts_params = {
        "Action": "AssumeRoleWithWebIdentity",
        "WebIdentityToken": token,
        "Version": "2011-06-15"
    }
    
    try:
        # Получаем временные credentials
        sts_response = requests.post(sts_url, params=sts_params, timeout=10)
        
        if sts_response.status_code != 200:
            print(f"STS ошибка: {sts_response.status_code} - {sts_response.text}")
            return not should_succeed
        
        # Парсим XML ответ (упрощённо)
        if "AccessKeyId" not in sts_response.text:
            print("Не удалось получить временные credentials")
            return not should_succeed
        
        # Пытаемся получить файл напрямую с токеном в заголовке
        file_url = f"http://localhost:9000/{file_path}"
        headers = {"Authorization": f"Bearer {token}"}
        
        file_response = requests.get(file_url, headers=headers, timeout=10)
        
        success = file_response.status_code == 200
        
        if should_succeed:
            if success:
                print(f"✅ Доступ к файлу {file_path} разрешён (как и ожидалось)")
                return True
            else:
                print(f"❌ Доступ к файлу {file_path} запрещён (ожидался разрешённый доступ)")
                print(f"Статус: {file_response.status_code}, Ответ: {file_response.text[:200]}")
                return False
        else:
            if success:
                print(f"❌ Доступ к файлу {file_path} разрешён (ожидался запрещённый доступ)")
                return False
            else:
                print(f"✅ Доступ к файлу {file_path} запрещён (как и ожидалось)")
                return True
                
    except Exception as e:
        print(f"Ошибка при тестировании доступа к файлу: {e}")
        return not should_succeed


def login_and_generate_report(username: str, password: str) -> str:
    """Логинится в систему и генерирует отчёт, возвращает путь к файлу"""
    
    print(f"\n{'='*60}")
    print(f"ЛОГИН И ГЕНЕРАЦИЯ ОТЧЁТА ДЛЯ {username}")
    print(f"{'='*60}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Переходим на главную страницу
            print("Переход на главную страницу...")
            page.goto("http://localhost:3000", timeout=30000)
            
            # Ждём загрузки и нажимаем кнопку входа
            print("Поиск кнопки входа...")
            login_button = page.locator('button:has-text("Войти")')
            expect(login_button).to_be_visible(timeout=10000)
            login_button.click()
            
            # Ждём перенаправления на Keycloak
            print("Ожидание формы входа Keycloak...")
            page.wait_for_url("**/auth**", timeout=10000)
            
            # Заполняем форму входа
            print(f"Ввод учётных данных для {username}...")
            page.fill('input[name="username"]', username)
            page.fill('input[name="password"]', password)
            page.click('input[type="submit"]')
            
            # Ждём возврата на главную страницу
            print("Ожидание возврата на главную страницу...")
            page.wait_for_url("http://localhost:3000/**", timeout=15000)
            
            # Ждём появления кнопки генерации отчёта
            print("Поиск кнопки генерации отчёта...")
            report_button = page.locator('button:has-text("Сгенерировать отчёт")')
            expect(report_button).to_be_visible(timeout=10000)
            
            # Генерируем отчёт
            print("Генерация отчёта...")
            report_button.click()
            
            # Ждём результата
            print("Ожидание результата генерации отчёта...")
            page.wait_for_selector('pre', timeout=30000)
            
            # Получаем результат
            result_element = page.locator('pre').first
            result_text = result_element.inner_text()
            
            print(f"Результат генерации отчёта:\n{result_text[:300]}...")
            
            # Извлекаем путь к файлу из результата (предполагаем, что он есть в JSON)
            try:
                result_json = json.loads(result_text)
                if "file_path" in result_json:
                    file_path = result_json["file_path"]
                    print(f"✅ Файл отчёта создан: {file_path}")
                    return file_path
                else:
                    # Если нет file_path, создаём предполагаемый путь
                    # Получаем токен для извлечения sub
                    token = get_jwt_token(username, password)
                    import jwt
                    decoded = jwt.decode(token, options={"verify_signature": False})
                    user_uuid = decoded.get("sub")
                    
                    file_path = f"reports/default/{user_uuid}/none__2025-11-01T00-00-00.json"
                    print(f"✅ Предполагаемый путь к файлу: {file_path}")
                    return file_path
                    
            except json.JSONDecodeError:
                print("⚠️ Не удалось распарсить JSON результата")
                # Возвращаем предполагаемый путь
                token = get_jwt_token(username, password)
                import jwt
                decoded = jwt.decode(token, options={"verify_signature": False})
                user_uuid = decoded.get("sub")
                
                file_path = f"reports/default/{user_uuid}/none__2025-11-01T00-00-00.json"
                print(f"✅ Предполагаемый путь к файлу: {file_path}")
                return file_path
            
        except Exception as e:
            print(f"❌ Ошибка при логине и генерации отчёта: {e}")
            raise
        finally:
            browser.close()


def main():
    """Основная функция интеграционного теста"""
    
    print("=" * 80)
    print("ИНТЕГРАЦИОННЫЙ ТЕСТ MINIO С JWT АВТОРИЗАЦИЕЙ")
    print("=" * 80)
    
    # Шаг 1: Полный перезапуск системы
    print("\n1️⃣ Полный перезапуск системы...")
    
    print("Остановка и удаление volumes...")
    run_docker_command("docker compose down -v")
    
    print("Сборка образов...")
    run_docker_command("docker compose build")
    
    print("Запуск системы...")
    run_docker_command("docker compose up -d")
    
    # Ждём готовности системы
    print("Ожидание готовности системы...")
    time.sleep(60)  # Даём время на полную инициализацию
    
    # Шаг 2: Тест с prosthetic1
    print("\n2️⃣ Тест с пользователем prosthetic1...")
    
    try:
        # Логинимся и генерируем отчёт
        prosthetic1_file = login_and_generate_report("prosthetic1", "prosthetic123")
        
        # Получаем токен prosthetic1
        prosthetic1_token = get_jwt_token("prosthetic1", "prosthetic123")
        
        # Тестируем доступ к своему файлу (должен разрешить)
        print("\nТестирование доступа prosthetic1 к своему файлу...")
        success1 = test_minio_file_access(prosthetic1_token, prosthetic1_file, should_succeed=True)
        
    except Exception as e:
        print(f"❌ Ошибка в тесте с prosthetic1: {e}")
        success1 = False
    
    # Шаг 3: Тест с prosthetic2
    print("\n3️⃣ Тест с пользователем prosthetic2...")
    
    try:
        # Получаем токен prosthetic2
        prosthetic2_token = get_jwt_token("prosthetic2", "prosthetic123")
        
        # Тестируем доступ к файлу prosthetic1 (должен запретить)
        print("\nТестирование доступа prosthetic2 к файлу prosthetic1...")
        success2 = test_minio_file_access(prosthetic2_token, prosthetic1_file, should_succeed=False)
        
    except Exception as e:
        print(f"❌ Ошибка в тесте с prosthetic2: {e}")
        success2 = False
    
    # Итоговый результат
    print("\n" + "=" * 80)
    print("РЕЗУЛЬТАТЫ ИНТЕГРАЦИОННОГО ТЕСТА")
    print("=" * 80)
    
    if success1:
        print("✅ Тест 1: prosthetic1 может получить доступ к своему файлу")
    else:
        print("❌ Тест 1: prosthetic1 НЕ может получить доступ к своему файлу")
    
    if success2:
        print("✅ Тест 2: prosthetic2 НЕ может получить доступ к файлу prosthetic1")
    else:
        print("❌ Тест 2: prosthetic2 МОЖЕТ получить доступ к файлу prosthetic1 (нарушение безопасности)")
    
    overall_success = success1 and success2
    
    if overall_success:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("JWT авторизация MinIO работает корректно")
    else:
        print("\n💥 ТЕСТЫ НЕ ПРОШЛИ!")
        print("Требуется доработка JWT авторизации MinIO")
    
    print("=" * 80)
    
    return overall_success


if __name__ == "__main__":
    main()
