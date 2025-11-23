"""
E2E тесты для веб-приложения с авторизацией через Keycloak.
Тесты проверяют фронтенд (localhost:5173), бэкенд (localhost:3001) и процесс авторизации.
"""

import json
import time
import httpx
import pytest
from playwright.sync_api import Page, expect


class TestServiceAvailability:
    """Тесты доступности сервисов."""
    
    def test_frontend_responds(self, frontend_url: str):
        """Проверка, что фронтенд отвечает на запросы."""
        print(f"\n=== Тест: Проверка доступности фронтенда ===")
        print(f"Проверяем URL: {frontend_url}")
        
        # Используем httpx для проверки доступности
        response = httpx.get(frontend_url, follow_redirects=True, timeout=10.0)
        
        # Проверяем, что получили успешный ответ
        assert response.status_code == 200, f"Фронтенд не отвечает, статус: {response.status_code}"
        print(f"✓ Фронтенд доступен, статус код: {response.status_code}")
        print(f"=== Тест завершен успешно ===\n")
    
    def test_backend_responds(self, backend_url: str):
        """Проверка, что бэкенд отвечает на запросы."""
        print(f"\n=== Тест: Проверка доступности бэкенда ===")
        print(f"Проверяем URL: {backend_url}/jwt")
        
        # Используем httpx для проверки доступности (проверяем /jwt эндпоинт)
        response = httpx.get(f"{backend_url}/jwt", timeout=10.0)
        
        # Проверяем, что получили ответ 200 с {"jwt": null}
        assert response.status_code == 200, f"Ожидали статус 200, получили: {response.status_code}"
        
        response_data = response.json()
        assert "jwt" in response_data, f"Неожиданный ответ: {response_data}"
        
        print(f"✓ Бэкенд доступен, статус код: {response.status_code}")
        print(f"✓ Ответ бэкенда: {response_data}")
        print(f"=== Тест завершен успешно ===\n")


class TestKeycloakAuthentication:
    """Тесты авторизации через Keycloak."""
    
    def test_login_flow(
        self,
        page: Page,
        frontend_url: str,
        test_user: dict
    ):
        """Полный тест процесса авторизации через Keycloak."""
        print(f"\n=== Тест: Полный процесс авторизации через Keycloak ===")
        
        # Шаг 1: Открываем фронтенд
        print(f"1. Открываем фронтенд: {frontend_url}")
        page.goto(frontend_url)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        current_url = page.url
        print(f"✓ Страница загружена, текущий URL: {current_url}")
        
        # Шаг 2: Проверяем, что произошел автоматический редирект на Keycloak
        print("2. Проверяем редирект на страницу авторизации Keycloak")
        
        # Keycloak автоматически редиректит на страницу входа
        # Проверяем, что мы на странице Keycloak (порт 8080)
        if "localhost:8080" in current_url or "8080" in current_url:
            print(f"✓ Автоматический редирект на Keycloak выполнен")
            
            # Шаг 3: Вводим учетные данные
            print(f"3. Вводим учетные данные: username={test_user['username']}")
            
            # Ищем поля ввода (Keycloak использует id="username" и id="password")
            username_field = page.locator('input#username, input[name="username"]').first
            password_field = page.locator('input#password, input[name="password"]').first
            
            # Проверяем, что поля видны
            expect(username_field).to_be_visible(timeout=10000)
            expect(password_field).to_be_visible(timeout=10000)
            
            # Заполняем поля
            username_field.fill(test_user["username"])
            password_field.fill(test_user["password"])
            
            print(f"✓ Учетные данные введены")
            
            # Шаг 4: Нажимаем кнопку входа
            print("4. Нажимаем кнопку входа")
            submit_button = page.locator('input[type="submit"], button[type="submit"]').first
            submit_button.click()
            
            # Шаг 5: Ждем редиректа обратно на фронтенд
            print("5. Ожидаем редиректа обратно на фронтенд")
            page.wait_for_load_state("networkidle")
            time.sleep(5)  # Даем время на обработку токена и рендеринг React
            
            current_url = page.url
            print(f"✓ Текущий URL после входа: {current_url}")
            
            # Делаем скриншот для отладки
            page.screenshot(path="/tmp/keycloak_after_login.png")
            print("✓ Скриншот сохранен: /tmp/keycloak_after_login.png")
        else:
            print("✓ Пользователь уже авторизован, редирект не требуется")
        
        # Шаг 6: Проверяем, что авторизация прошла успешно
        print("6. Проверяем, что авторизация прошла успешно")
        
        # После успешной авторизации должен отображаться заголовок "✓ Вы авторизованы!"
        # и кнопка "Вызвать GET /reports"
        auth_heading = page.locator('h1:has-text("Вы авторизованы")')
        expect(auth_heading).to_be_visible(timeout=15000)
        print("✓ Найден заголовок 'Вы авторизованы!'")
        
        reports_button = page.locator('button:has-text("Посмотреть JWT")')
        expect(reports_button).to_be_visible(timeout=10000)
        print("✓ Найдена кнопка 'Посмотреть JWT'")
        
        # Шаг 7: Проверяем, что фронтенд после редиректа что-то показывает
        print("7. Проверяем содержимое страницы после авторизации")
        
        # Делаем скриншот для визуальной проверки
        screenshot_path = "/tmp/keycloak_auth_success.png"
        page.screenshot(path=screenshot_path)
        print(f"✓ Скриншот сохранен: {screenshot_path}")
        
        # Проверяем, что на странице есть контент
        body_text = page.locator('body').inner_text()
        assert len(body_text) > 0, "Страница пустая после авторизации"
        print(f"✓ Страница содержит текст ({len(body_text)} символов)")
        
        print(f"=== Тест завершен успешно ===\n")
    
    def test_reports_button_shows_jwt(
        self,
        page: Page,
        frontend_url: str,
        backend_url: str,
        test_user: dict
    ):
        """Тест проверки JWT токена при нажатии на кнопку reports_api/jwt."""
        print(f"\n=== Тест: Проверка отображения JWT при нажатии на кнопку reports_api/jwt ===")
        
        # Шаг 1: Авторизуемся (если еще не авторизованы)
        print(f"1. Открываем фронтенд и авторизуемся")
        page.goto(frontend_url)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        current_url = page.url
        
        # Проверяем, нужна ли авторизация (редирект на Keycloak)
        if "localhost:8080" in current_url or "8080" in current_url:
            print("   Выполняем авторизацию через Keycloak...")
            
            username_field = page.locator('input#username, input[name="username"]').first
            password_field = page.locator('input#password, input[name="password"]').first
            
            username_field.fill(test_user["username"])
            password_field.fill(test_user["password"])
            
            submit_button = page.locator('input[type="submit"], button[type="submit"]').first
            submit_button.click()
            
            page.wait_for_load_state("networkidle")
            time.sleep(5)
            print("✓ Авторизация выполнена")
        else:
            print("✓ Пользователь уже авторизован")
        
        # Шаг 2: Нажимаем на кнопку Вызвать GET /reports
        print("2. Нажимаем кнопку 'Посмотреть JWT'")
        reports_button = page.locator('button:has-text("Посмотреть JWT")')
        expect(reports_button).to_be_visible(timeout=10000)
        
        # Нажимаем кнопку
        print("3. Нажимаем кнопку")
        reports_button.click()
        
        # Ждем загрузки JWT
        print("4. Ожидаем загрузки JWT")
        time.sleep(3)
        
        # Проверяем, что на странице отобразился JWT
        print("5. Проверяем отображение JWT на странице")
        
        # Проверяем, что на странице есть текст "✓ JWT получен от reports_api:"
        jwt_success = page.locator('text="✓ JWT получен от reports_api:"')
        expect(jwt_success).to_be_visible(timeout=10000)
        print(f"✓ JWT отобразился на странице")
        
        # Проверяем структуру JWT через текст на странице
        body_text = page.locator('body').inner_text()
        assert 'sub' in body_text or 'preferred_username' in body_text, "Не найдены поля JWT на странице"
        print(f"✓ JWT содержит ожидаемые поля")
        
        # Шаг 6: Проверяем, что на странице отображается какая-то информация
        print("6. Проверяем отображение информации на странице")
        
        # Ждем появления ответа от бэкенда
        time.sleep(2)
        
        # Проверяем, что нет ошибок
        error_div = page.locator('div.bg-red-50, div.bg-red-100')
        if error_div.is_visible():
            error_text = error_div.inner_text()
            print(f"⚠ Обнаружена ошибка на странице: {error_text}")
            # Если есть ошибка, тест должен упасть
            raise AssertionError(f"Бэкенд вернул ошибку: {error_text}")
        else:
            print("✓ Ошибок на странице не обнаружено")
        
        # Проверяем, что есть успешный ответ от бэкенда
        status_code_element = page.locator('text=/HTTP статус код:/')
        if status_code_element.is_visible():
            status_text = page.locator('span.font-mono').first.inner_text()
            print(f"✓ HTTP статус код от бэкенда: {status_text}")
            
            # Проверяем, что статус код 200
            assert status_text == "200", f"Ожидали статус 200, получили: {status_text}"
            
            # Проверяем, что есть ответ от сервера
            response_section = page.locator('text=/Ответ от сервера:/')
            if response_section.is_visible():
                print("✓ Получен ответ от бэкенда")
                
                # Получаем JSON ответ
                response_json = page.locator('pre.bg-gray-100').nth(1).inner_text()
                print(f"✓ Ответ содержит данные ({len(response_json)} символов)")
                
                # Проверяем, что в ответе есть payload
                assert "payload" in response_json, "Ответ не содержит поле 'payload'"
                print("✓ Ответ содержит поле 'payload' с данными JWT")
        
        # Делаем скриншот
        screenshot_path = "/tmp/keycloak_reports_jwt.png"
        page.screenshot(path=screenshot_path)
        print(f"✓ Скриншот сохранен: {screenshot_path}")
        
        print(f"=== Тест завершен успешно ===\n")


class TestFullE2EFlow:
    """Полный E2E тест всего процесса."""
    
    def test_complete_flow(
        self,
        page: Page,
        frontend_url: str,
        backend_url: str,
        test_user: dict
    ):
        """Полный E2E тест: проверка сервисов -> авторизация -> проверка JWT."""
        print(f"\n=== Полный E2E тест ===")
        
        # Очищаем cookies и контекст для чистого теста
        page.context.clear_cookies()
        
        # 1. Проверка доступности фронтенда
        print("1. Проверка доступности фронтенда")
        response = httpx.get(frontend_url, follow_redirects=True, timeout=10.0)
        assert response.status_code == 200
        print(f"✓ Фронтенд доступен")
        
        # 2. Проверка доступности бэкенда
        print("2. Проверка доступности бэкенда")
        response = httpx.get(f"{backend_url}/jwt", timeout=10.0)
        assert response.status_code == 200
        assert "jwt" in response.json()
        print(f"✓ Бэкенд доступен")
        
        # 3. Открываем фронтенд в браузере
        print("3. Открываем фронтенд в браузере")
        page.goto(frontend_url)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        print(f"✓ Фронтенд загружен")
        
        # 4. Авторизация через Keycloak
        print("4. Авторизация через Keycloak")
        current_url = page.url
        
        if "localhost:8080" in current_url or "8080" in current_url:
            print("   Выполняем вход через Keycloak...")
            
            username_field = page.locator('input#username, input[name="username"]').first
            password_field = page.locator('input#password, input[name="password"]').first
            
            username_field.fill(test_user["username"])
            password_field.fill(test_user["password"])
            
            submit_button = page.locator('input[type="submit"], button[type="submit"]').first
            submit_button.click()
            
            page.wait_for_load_state("networkidle")
            time.sleep(5)
            print(f"✓ Авторизация успешна")
        else:
            print(f"✓ Пользователь уже авторизован")
        
        # 5. Проверка отображения страницы после авторизации
        print("5. Проверка отображения страницы после авторизации")
        auth_heading = page.locator('h1:has-text("Вы авторизованы")')
        expect(auth_heading).to_be_visible(timeout=15000)
        print(f"✓ Страница отображается корректно")
        
        # 6. Нажатие на кнопку и проверка JWT
        print("6. Нажатие на кнопку 'Посмотреть JWT'")
        reports_button = page.locator('button:has-text("Посмотреть JWT")')
        expect(reports_button).to_be_visible(timeout=10000)
        
        reports_button.click()
        time.sleep(3)
        
        # 7. Проверка отображения JWT
        print("7. Проверка отображения JWT на странице")
        jwt_success = page.locator('text="✓ JWT получен от reports_api:"')
        expect(jwt_success).to_be_visible(timeout=10000)
        print(f"✓ JWT отобразился на странице")
        
        # Финальный скриншот
        screenshot_path = "/tmp/keycloak_full_e2e.png"
        page.screenshot(path=screenshot_path)
        print(f"✓ Скриншот сохранен: {screenshot_path}")
        
        print(f"\n=== Полный E2E тест завершен успешно ===\n")


class TestExternalUUID:
    """Тесты для проверки external_uuid в JWT для LDAP-пользователей."""
    
    def test_ldap_user_has_external_uuid(
        self,
        page: Page,
        frontend_url: str,
        backend_url: str
    ):
        """
        Проверка, что LDAP-пользователь (customer1) имеет external_uuid в JWT.
        """
        print(f"\n=== Тест: Проверка external_uuid для LDAP-пользователя customer1 ===")
        
        # Используем customer1 из LDAP
        ldap_user = {
            "username": "customer1",
            "password": "customer1_password"
        }
        
        # Шаг 1: Авторизуемся как customer1
        print(f"1. Открываем фронтенд и авторизуемся как {ldap_user['username']}")
        page.goto(frontend_url)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        current_url = page.url
        
        if "localhost:8080" in current_url or "8080" in current_url:
            print("   Выполняем авторизацию через Keycloak...")
            
            username_field = page.locator('input#username, input[name="username"]').first
            password_field = page.locator('input#password, input[name="password"]').first
            
            expect(username_field).to_be_visible(timeout=10000)
            expect(password_field).to_be_visible(timeout=10000)
            
            username_field.fill(ldap_user["username"])
            password_field.fill(ldap_user["password"])
            
            submit_button = page.locator('input[type="submit"], button[type="submit"]').first
            submit_button.click()
            
            page.wait_for_load_state("networkidle")
            time.sleep(5)
            print("✓ Авторизация выполнена")
        else:
            print("✓ Пользователь уже авторизован")
        
        # Шаг 2: Нажимаем кнопку "Посмотреть JWT"
        print("2. Нажимаем кнопку 'Посмотреть JWT'")
        jwt_button = page.locator('button:has-text("Посмотреть JWT")')
        expect(jwt_button).to_be_visible(timeout=10000)
        
        jwt_button.click()
        time.sleep(3)
        
        # Шаг 3: Проверяем наличие external_uuid в JWT
        print("3. Проверяем наличие external_uuid в JWT")
        
        # Получаем содержимое JWT с страницы
        jwt_content = page.locator('pre.bg-gray-100').last.inner_text()
        print(f"✓ JWT получен ({len(jwt_content)} символов)")
        
        # Парсим JSON
        try:
            jwt_data = json.loads(jwt_content)
            
            # Проверяем наличие external_uuid
            assert "external_uuid" in jwt_data, "JWT не содержит поле external_uuid для LDAP-пользователя"
            print(f"✓ JWT содержит поле external_uuid: {jwt_data['external_uuid']}")
            
            # Проверяем, что external_uuid соответствует ожидаемому значению для customer1
            expected_uuid = "13737288-edf4-4b14-82ad-8590a4d7c306"
            assert jwt_data["external_uuid"] == expected_uuid, \
                f"external_uuid не соответствует ожидаемому: {jwt_data['external_uuid']} != {expected_uuid}"
            print(f"✓ external_uuid соответствует ожидаемому значению")
            
            # Проверяем, что также есть поле sub
            assert "sub" in jwt_data, "JWT не содержит поле sub"
            print(f"✓ JWT также содержит поле sub: {jwt_data['sub']}")
            
        except json.JSONDecodeError as e:
            print(f"✗ Не удалось распарсить JWT как JSON: {e}")
            print(f"   Содержимое: {jwt_content[:200]}...")
            raise AssertionError("JWT не является валидным JSON")
        
        # Делаем скриншот
        screenshot_path = "/tmp/keycloak_ldap_external_uuid.png"
        page.screenshot(path=screenshot_path)
        print(f"✓ Скриншот сохранен: {screenshot_path}")
        
        print(f"=== Тест завершен успешно ===\n")
    
    def test_local_user_no_external_uuid(
        self,
        page: Page,
        frontend_url: str,
        backend_url: str,
        test_user: dict
    ):
        """
        Проверка, что локальный пользователь Keycloak (prosthetic1) НЕ имеет external_uuid в JWT.
        """
        print(f"\n=== Тест: Проверка отсутствия external_uuid для локального пользователя prosthetic1 ===")
        
        # Используем prosthetic1 из локального Keycloak
        local_user = {
            "username": "prosthetic1",
            "password": "prosthetic123"
        }
        
        # Шаг 1: Авторизуемся как prosthetic1
        print(f"1. Открываем фронтенд и авторизуемся как {local_user['username']}")
        page.goto(frontend_url)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        current_url = page.url
        
        if "localhost:8080" in current_url or "8080" in current_url:
            print("   Выполняем авторизацию через Keycloak...")
            
            username_field = page.locator('input#username, input[name="username"]').first
            password_field = page.locator('input#password, input[name="password"]').first
            
            expect(username_field).to_be_visible(timeout=10000)
            expect(password_field).to_be_visible(timeout=10000)
            
            username_field.fill(local_user["username"])
            password_field.fill(local_user["password"])
            
            submit_button = page.locator('input[type="submit"], button[type="submit"]').first
            submit_button.click()
            
            page.wait_for_load_state("networkidle")
            time.sleep(5)
            print("✓ Авторизация выполнена")
        else:
            print("✓ Пользователь уже авторизован")
        
        # Шаг 2: Нажимаем кнопку "Посмотреть JWT"
        print("2. Нажимаем кнопку 'Посмотреть JWT'")
        jwt_button = page.locator('button:has-text("Посмотреть JWT")')
        expect(jwt_button).to_be_visible(timeout=10000)
        
        jwt_button.click()
        time.sleep(3)
        
        # Шаг 3: Проверяем ОТСУТСТВИЕ external_uuid в JWT
        print("3. Проверяем отсутствие external_uuid в JWT")
        
        # Получаем содержимое JWT с страницы
        jwt_content = page.locator('pre.bg-gray-100').last.inner_text()
        print(f"✓ JWT получен ({len(jwt_content)} символов)")
        
        # Парсим JSON
        try:
            jwt_data = json.loads(jwt_content)
            
            # Проверяем ОТСУТСТВИЕ external_uuid
            if "external_uuid" in jwt_data:
                print(f"✗ JWT содержит поле external_uuid для локального пользователя: {jwt_data['external_uuid']}")
                raise AssertionError("JWT не должен содержать external_uuid для локального пользователя Keycloak")
            
            print(f"✓ JWT не содержит поле external_uuid (как и ожидалось)")
            
            # Проверяем, что есть поле sub
            assert "sub" in jwt_data, "JWT не содержит поле sub"
            print(f"✓ JWT содержит поле sub: {jwt_data['sub']}")
            
            # Проверяем, что sub соответствует UUID prosthetic1
            expected_sub = "54885c9b-6eea-48f7-89f9-353ad8273e95"
            assert jwt_data["sub"] == expected_sub, \
                f"sub не соответствует ожидаемому: {jwt_data['sub']} != {expected_sub}"
            print(f"✓ sub соответствует ожидаемому значению")
            
        except json.JSONDecodeError as e:
            print(f"✗ Не удалось распарсить JWT как JSON: {e}")
            print(f"   Содержимое: {jwt_content[:200]}...")
            raise AssertionError("JWT не является валидным JSON")
        
        # Делаем скриншот
        screenshot_path = "/tmp/keycloak_local_no_external_uuid.png"
        page.screenshot(path=screenshot_path)
        print(f"✓ Скриншот сохранен: {screenshot_path}")
        
        print(f"=== Тест завершен успешно ===\n")
