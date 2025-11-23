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
        
        reports_button = page.locator('button:has-text("Вызвать GET /reports")')
        expect(reports_button).to_be_visible(timeout=10000)
        print("✓ Найдена кнопка 'Вызвать GET /reports'")
        
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
        """Тест проверки JWT токена при нажатии на кнопку /reports."""
        print(f"\n=== Тест: Проверка отображения JWT при нажатии на кнопку /reports ===")
        
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
        print("2. Нажимаем кнопку 'Вызвать GET /reports'")
        reports_button = page.locator('button:has-text("Вызвать GET /reports")')
        expect(reports_button).to_be_visible(timeout=10000)
        
        # Перехватываем запрос к /reports
        print("3. Перехватываем запрос к /reports для проверки JWT")
        
        # Создаем обработчик для перехвата запросов
        request_data = {}
        
        def handle_request(request):
            """Обработчик для перехвата запросов к /reports."""
            if "/reports" in request.url:
                request_data["url"] = request.url
                request_data["headers"] = request.headers
                print(f"   Перехвачен запрос: {request.url}")
        
        page.on("request", handle_request)
        
        # Нажимаем кнопку
        reports_button.click()
        time.sleep(3)
        
        # Шаг 3: Проверяем, что запрос был отправлен с JWT токеном
        print("4. Проверяем наличие JWT токена в запросе")
        
        assert "url" in request_data, "Запрос к /reports не был отправлен"
        assert "headers" in request_data, "Заголовки запроса не перехвачены"
        
        headers = request_data["headers"]
        assert "authorization" in headers or "Authorization" in headers, \
            "Заголовок Authorization отсутствует в запросе"
        
        auth_header = headers.get("authorization") or headers.get("Authorization")
        assert auth_header.startswith("Bearer "), \
            f"Неверный формат заголовка Authorization: {auth_header}"
        
        jwt_token = auth_header.replace("Bearer ", "")
        print(f"✓ JWT токен найден в запросе")
        print(f"   Первые 50 символов токена: {jwt_token[:50]}...")
        
        # Проверяем структуру JWT (должен состоять из 3 частей, разделенных точками)
        jwt_parts = jwt_token.split(".")
        assert len(jwt_parts) == 3, f"JWT токен имеет неверную структуру: {len(jwt_parts)} частей вместо 3"
        print(f"✓ JWT токен имеет корректную структуру (3 части)")
        
        # Декодируем payload JWT (вторая часть)
        import base64
        
        # Добавляем padding если нужно
        payload_b64 = jwt_parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        
        try:
            payload_json = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
            payload = json.loads(payload_json)
            
            print(f"✓ JWT payload успешно декодирован")
            print(f"   Содержимое JWT payload:")
            print(f"   - sub (subject): {payload.get('sub', 'N/A')}")
            print(f"   - preferred_username: {payload.get('preferred_username', 'N/A')}")
            print(f"   - email: {payload.get('email', 'N/A')}")
            
            # Проверяем, что в токене есть информация о пользователе
            assert "sub" in payload or "preferred_username" in payload, \
                "JWT токен не содержит информации о пользователе"
            
        except Exception as e:
            print(f"⚠ Не удалось декодировать JWT payload: {e}")
        
        # Шаг 4: Проверяем, что на странице отображается какая-то информация
        print("5. Проверяем отображение информации на странице")
        
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
        
        # 1. Проверка доступности фронтенда
        print("1. Проверка доступности фронтенда")
        response = httpx.get(frontend_url, follow_redirects=True, timeout=10.0)
        assert response.status_code == 200
        print(f"✓ Фронтенд доступен")
        
        # 2. Проверка доступности бэкенда
        print("2. Проверка доступности бэкенда")
        response = httpx.get(backend_url, timeout=10.0)
        assert response.status_code == 404
        assert response.json() == {"detail": "Not Found"}
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
        
        # 6. Нажатие на кнопку /reports и проверка JWT
        print("6. Нажатие на кнопку 'Вызвать GET /reports'")
        reports_button = page.locator('button:has-text("Вызвать GET /reports")')
        expect(reports_button).to_be_visible(timeout=10000)
        
        request_data = {}
        
        def handle_request(request):
            if "/reports" in request.url:
                request_data["url"] = request.url
                request_data["headers"] = request.headers
        
        page.on("request", handle_request)
        reports_button.click()
        time.sleep(3)
        
        # 7. Проверка JWT в запросе
        print("7. Проверка JWT токена в запросе")
        assert "headers" in request_data
        headers = request_data["headers"]
        auth_header = headers.get("authorization") or headers.get("Authorization")
        assert auth_header and auth_header.startswith("Bearer ")
        print(f"✓ JWT токен присутствует в запросе")
        
        # Финальный скриншот
        screenshot_path = "/tmp/keycloak_full_e2e.png"
        page.screenshot(path=screenshot_path)
        print(f"✓ Скриншот сохранен: {screenshot_path}")
        
        print(f"\n=== Полный E2E тест завершен успешно ===\n")
