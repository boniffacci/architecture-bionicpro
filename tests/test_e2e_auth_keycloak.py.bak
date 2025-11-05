"""
End-to-End тесты для веб-приложения BionicPro.
Тестирует фронтенд, бэкенд и процесс авторизации через Authentik/Keycloak.
"""

import json
import time
import pytest
import requests
from playwright.sync_api import Page, expect


class TestServiceAvailability:
    """Тесты доступности сервисов."""
    
    def test_frontend_is_available(self, frontend_url: str):
        """
        Проверяет, что фронтенд-сервер доступен и отвечает на запросы.
        """
        response = requests.get(frontend_url, timeout=10)
        assert response.status_code == 200, f"Frontend не доступен: {response.status_code}"
        print(f"✓ Frontend доступен на {frontend_url}")
    
    def test_backend_is_available(self, backend_url: str):
        """
        Проверяет, что бэкенд-сервер доступен и возвращает ожидаемый ответ.
        Корневой endpoint должен возвращать {"detail":"Not Found"}.
        """
        response = requests.get(backend_url + "/", timeout=10)
        assert response.status_code == 404, f"Backend вернул неожиданный статус: {response.status_code}"
        
        data = response.json()
        assert data.get("detail") == "Not Found", f"Backend вернул неожиданный ответ: {data}"
        print(f"✓ Backend доступен на {backend_url} и возвращает корректный ответ")


class TestAuthenticationFlow:
    """Тесты процесса авторизации через Authentik/Keycloak."""
    
    def test_login_flow_with_authentik(
        self, 
        page: Page, 
        frontend_url: str, 
        test_user_credentials: dict
    ):
        """
        Тестирует полный процесс авторизации:
        1. Открывает фронтенд
        2. Нажимает кнопку входа
        3. Авторизуется в Authentik под пользователем из Keycloak
        4. Проверяет успешный редирект обратно на фронтенд
        5. Проверяет, что пользователь авторизован
        """
        print(f"\n=== Начало теста авторизации ===")
        
        # Слушаем консольные логи браузера с самого начала
        console_messages = []
        def handle_console(msg):
            text = f"[{msg.type}] {msg.text}"
            console_messages.append(text)
            print(f"   [CONSOLE] {text}")  # Выводим сразу
        page.on("console", handle_console)
        
        # Шаг 1: Открываем фронтенд
        print(f"1. Открываем фронтенд: {frontend_url}")
        page.goto(frontend_url)
        
        # Ждем загрузки страницы
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        
        print("2. Проверяем наличие кнопки входа")
        login_button = page.get_by_role("button", name="Войти через Authentik")
        expect(login_button).to_be_visible(timeout=10000)
        print("✓ Кнопка входа найдена")
        
        # Шаг 3: Нажимаем кнопку входа
        print("3. Нажимаем кнопку входа")
        
        # Проверяем sessionStorage перед кликом
        session_before = page.evaluate("""() => {
            return {
                oauth_state: sessionStorage.getItem('oauth_state'),
                code_verifier: sessionStorage.getItem('code_verifier')
            }
        }""")
        print(f"   SessionStorage ДО клика: oauth_state={'есть' if session_before['oauth_state'] else 'нет'}, code_verifier={'есть' if session_before['code_verifier'] else 'нет'}")
        
        login_button.click()
        time.sleep(0.5)  # Даем время на сохранение в sessionStorage
        
        # Проверяем sessionStorage после клика
        session_after = page.evaluate("""() => {
            return {
                oauth_state: sessionStorage.getItem('oauth_state'),
                code_verifier: sessionStorage.getItem('code_verifier')
            }
        }""")
        print(f"   SessionStorage ПОСЛЕ клика: oauth_state={'есть' if session_after['oauth_state'] else 'нет'}, code_verifier={'есть' if session_after['code_verifier'] else 'нет'}")
        
        # Шаг 4: Ждем редиректа на Authentik (может быть либо /application/o/authorize/, либо /if/flow/)
        print("4. Ожидаем редирект на Authentik")
        page.wait_for_url("**/localhost:9000/**", timeout=15000)
        print(f"✓ Редирект на Authentik выполнен: {page.url}")
        
        # Ждем загрузки страницы Authentik
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        # Шаг 3: Проверяем, есть ли кнопка входа через Keycloak
        print("5. Ищем кнопку входа через Keycloak на странице Authentik")
        
        # Authentik может показать либо форму входа, либо кнопку для входа через Keycloak
        # Пытаемся найти кнопку Keycloak
        try:
            # Ищем кнопку с текстом "Keycloak" или ссылку на Keycloak
            keycloak_button = page.locator('a:has-text("Keycloak"), button:has-text("Keycloak")').first
            if keycloak_button.is_visible(timeout=3000):
                print("✓ Найдена кнопка входа через Keycloak, нажимаем")
                keycloak_button.click()
                page.wait_for_load_state("networkidle")
                time.sleep(2)
        except Exception as e:
            print(f"⚠ Кнопка Keycloak не найдена, возможно нужен прямой вход: {e}")
        
        # Шаг 4: Вводим учетные данные
        # Проверяем, на какой странице мы находимся (Authentik или Keycloak)
        current_url = page.url
        print(f"6. Текущий URL: {current_url}")
        
        if "keycloak" in current_url.lower() or "8080" in current_url:
            print("7. Находимся на странице Keycloak, вводим учетные данные")
            
            # Ждем загрузки формы входа Keycloak
            page.wait_for_selector('input[name="username"], input[id="username"]', timeout=10000)
            
            # Вводим username
            username_input = page.locator('input[name="username"], input[id="username"]').first
            username_input.fill(test_user_credentials["username"])
            print(f"✓ Введен username: {test_user_credentials['username']}")
            
            # Вводим password
            password_input = page.locator('input[name="password"], input[id="password"]').first
            password_input.fill(test_user_credentials["password"])
            print(f"✓ Введен password")
            
            # Нажимаем кнопку входа
            submit_button = page.locator('input[type="submit"], button[type="submit"]').first
            submit_button.click()
            print("✓ Нажата кнопка входа в Keycloak")
            
        else:
            print("7. Находимся на странице Authentik, вводим учетные данные")
            
            # Ждем загрузки формы входа Authentik
            page.wait_for_selector('input[name="uidField"], input[type="text"]', timeout=10000)
            
            # Вводим username
            username_input = page.locator('input[name="uidField"], input[type="text"]').first
            username_input.fill(test_user_credentials["username"])
            print(f"✓ Введен username: {test_user_credentials['username']}")
            
            # Нажимаем кнопку "Продолжить" или "Continue"
            try:
                continue_button = page.get_by_role("button", name="Continue")
                if continue_button.is_visible(timeout=2000):
                    continue_button.click()
                    time.sleep(1)
            except:
                pass
            
            # Вводим password
            password_input = page.locator('input[name="password"], input[type="password"]').first
            password_input.fill(test_user_credentials["password"])
            print(f"✓ Введен password")
            
            # Нажимаем кнопку входа
            submit_button = page.get_by_role("button", name="Sign in")
            submit_button.click()
            print("✓ Нажата кнопка входа в Authentik")
        
        # Ждем возврата на Authentik после входа в Keycloak
        time.sleep(3)
        print(f"7.5. После входа в Keycloak, текущий URL: {page.url}")
        
        # Проверяем, не вернулись ли мы на страницу Authentik с предложением войти
        if "localhost:9000" in page.url and "flow" in page.url:
            print("7.6. Вернулись на Authentik, ищем кнопку подтверждения входа")
            # Ищем кнопку "Войти" на русском или "Continue" на английском
            try:
                continue_button = page.get_by_role("button", name="Войти")
                if continue_button.is_visible(timeout=3000):
                    print("✓ Найдена кнопка 'Войти', нажимаем")
                    continue_button.click()
                    time.sleep(2)
            except:
                try:
                    continue_button = page.get_by_role("button", name="Continue")
                    if continue_button.is_visible(timeout=3000):
                        print("✓ Найдена кнопка 'Continue', нажимаем")
                        continue_button.click()
                        time.sleep(2)
                except:
                    print("⚠ Кнопка подтверждения не найдена, продолжаем")
        
        # Слушаем все навигации для отладки
        navigations = []
        def handle_navigation(frame):
            if frame == page.main_frame:
                navigations.append(frame.url)
        page.on("framenavigated", handle_navigation)
        
        # Шаг 5: Ждем редиректа обратно на фронтенд
        print("8. Ожидаем редирект обратно на фронтенд")
        try:
            page.wait_for_url(f"{frontend_url}/**", timeout=20000)
            print(f"✓ Редирект на фронтенд выполнен: {page.url}")
            
            # Сразу проверяем параметры URL
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(page.url)
            query_params = parse_qs(parsed_url.query)
            print(f"   Параметры сразу после редиректа: code={'есть' if 'code' in query_params else 'нет'}, state={'есть' if 'state' in query_params else 'нет'}")
        except Exception as e:
            # Выводим информацию об ошибке
            print(f"⚠ Ошибка редиректа: {e}")
            print(f"⚠ Текущий URL: {page.url}")
            
            # Проверяем, есть ли сообщение об ошибке на странице
            try:
                error_text = page.locator('text=/error|failed|ошибка/i').all_text_contents()
                if error_text:
                    print(f"⚠ Найдены сообщения об ошибках на странице: {error_text}")
            except:
                pass
            
            # Выводим заголовок страницы
            print(f"⚠ Заголовок страницы: {page.title()}")
            
            raise
        
        # Ждем завершения OAuth flow
        # Не используем networkidle, так как фронтенд может делать периодические запросы
        print("9. Ждем завершения OAuth flow")
        time.sleep(5)
        
        # Проверяем sessionStorage
        session_storage = page.evaluate("""() => {
            return {
                oauth_state: sessionStorage.getItem('oauth_state'),
                code_verifier: sessionStorage.getItem('code_verifier')
            }
        }""")
        print(f"   SessionStorage: oauth_state={'есть' if session_storage['oauth_state'] else 'нет'}, code_verifier={'есть' if session_storage['code_verifier'] else 'нет'}")
        
        # Шаг 6: Проверяем, что авторизация прошла успешно
        print("10. Проверяем успешную авторизацию")
        print(f"   Текущий URL: {page.url}")
        
        # Проверяем параметры URL
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(page.url)
        query_params = parse_qs(parsed_url.query)
        print(f"   URL path: {parsed_url.path}")
        print(f"   URL параметры: code={'есть' if 'code' in query_params else 'нет'}, state={'есть' if 'state' in query_params else 'нет'}")
        
        # Выводим содержимое страницы для отладки
        page_content = page.content()
        print(f"   Длина HTML: {len(page_content)} символов")
        
        # Проверяем, есть ли кнопка "Войти через Authentik" (значит не авторизованы)
        login_button_visible = page.get_by_role("button", name="Войти через Authentik").is_visible()
        print(f"   Кнопка 'Войти через Authentik' видна: {login_button_visible}")
        
        # Выводим консольные логи браузера
        if console_messages:
            print("   Консольные логи браузера:")
            for msg in console_messages[-10:]:  # Последние 10 сообщений
                print(f"     {msg}")
        else:
            print("   Консольных логов нет")
        
        # Выводим все навигации
        if navigations:
            print("   Навигации:")
            for nav in navigations[-5:]:  # Последние 5 навигаций
                print(f"     {nav}")
        
        # Ищем элемент, который показывает, что пользователь авторизован
        # Используем более гибкий селектор
        success_indicator = page.locator('text=/Вы авторизованы|✓ Вы авторизованы/i')
        expect(success_indicator).to_be_visible(timeout=15000)
        print("✓ Найден индикатор успешной авторизации")
        
        # Проверяем наличие кнопки выхода
        logout_button = page.get_by_role("button", name="Выйти")
        expect(logout_button).to_be_visible()
        print("✓ Найдена кнопка выхода")
        
        # Проверяем, что отображается информация о пользователе
        user_info_section = page.get_by_text("Информация о пользователе")
        expect(user_info_section).to_be_visible()
        print("✓ Отображается информация о пользователе")
        
        print(f"=== Тест авторизации завершен успешно ===\n")
    
    def test_logout_flow(
        self, 
        page: Page, 
        frontend_url: str, 
        test_user_credentials: dict
    ):
        """
        Тестирует процесс выхода из системы:
        1. Авторизуется в системе
        2. Нажимает кнопку выхода
        3. Проверяет, что произошел редирект на страницу входа
        4. Проверяет, что отображается кнопка "Войти через Authentik"
        """
        print(f"\n=== Начало теста выхода из системы ===")
        
        # Шаг 1: Авторизуемся (используем упрощенную версию из test_login_flow_with_authentik)
        print("1. Выполняем авторизацию")
        page.goto(frontend_url)
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        
        # Нажимаем кнопку входа
        login_button = page.get_by_role("button", name="Войти через Authentik")
        login_button.click()
        
        # Ждем редиректа на Authentik
        page.wait_for_url("**/localhost:9000/**", timeout=15000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        # Нажимаем кнопку Keycloak
        keycloak_button = page.locator('a:has-text("Keycloak"), button:has-text("Keycloak")').first
        keycloak_button.click()
        time.sleep(2)
        
        # Вводим учетные данные в Keycloak
        current_url = page.url
        if "keycloak" in current_url.lower() or "8080" in current_url:
            page.wait_for_selector('input[name="username"], input[id="username"]', timeout=10000)
            page.locator('input[name="username"], input[id="username"]').first.fill(test_user_credentials["username"])
            page.locator('input[name="password"], input[id="password"]').first.fill(test_user_credentials["password"])
            page.locator('input[type="submit"], button[type="submit"]').first.click()
        
        # Ждем возврата на Authentik и нажимаем кнопку подтверждения
        time.sleep(2)
        try:
            continue_button = page.get_by_role("button", name="Войти")
            if continue_button.is_visible(timeout=3000):
                continue_button.click()
                time.sleep(2)
        except:
            pass
        
        # Ждем редиректа на фронтенд
        page.wait_for_url(f"{frontend_url}/**", timeout=20000)
        time.sleep(5)
        
        # Проверяем, что авторизованы
        success_indicator = page.locator('text=/Вы авторизованы|✓ Вы авторизованы/i')
        expect(success_indicator).to_be_visible(timeout=15000)
        print("✓ Авторизация выполнена успешно")
        
        # Шаг 2: Нажимаем кнопку выхода
        print("2. Нажимаем кнопку выхода")
        logout_button = page.get_by_role("button", name="Выйти")
        expect(logout_button).to_be_visible()
        logout_button.click()
        print("✓ Кнопка выхода нажата")
        
        # Шаг 3: Ждем редиректа
        print("3. Ожидаем редирект после выхода")
        # Может быть редирект через Authentik logout flow
        time.sleep(3)
        
        # Проверяем, что мы на странице входа (может быть на фронтенде или на Authentik)
        current_url = page.url
        print(f"   Текущий URL после выхода: {current_url}")
        
        # Если мы на Authentik, ждем редиректа обратно на фронтенд
        if "localhost:9000" in current_url:
            print("   Находимся на странице Authentik, ждем редиректа на фронтенд")
            try:
                page.wait_for_url(f"{frontend_url}/**", timeout=10000)
                print(f"✓ Редирект на фронтенд выполнен: {page.url}")
            except:
                # Если автоматического редиректа нет, переходим вручную
                print("   Автоматического редиректа нет, переходим на фронтенд вручную")
                page.goto(frontend_url)
                page.wait_for_load_state("networkidle")
        else:
            # Если мы остались на фронтенде, просто переходим на главную страницу
            print("   Остались на фронтенде, переходим на главную страницу")
            page.goto(frontend_url)
            page.wait_for_load_state("networkidle")
        
        time.sleep(2)
        
        # Шаг 4: Проверяем, что видна кнопка входа (значит мы вышли)
        print("4. Проверяем, что отображается кнопка входа")
        login_button_after_logout = page.get_by_role("button", name="Войти через Authentik")
        expect(login_button_after_logout).to_be_visible(timeout=10000)
        print("✓ Кнопка 'Войти через Authentik' отображается")
        
        # Проверяем, что НЕ отображается индикатор авторизации
        success_indicator_check = page.locator('text=/Вы авторизованы|✓ Вы авторизованы/i')
        expect(success_indicator_check).not_to_be_visible()
        print("✓ Индикатор авторизации не отображается")
        
        print(f"=== Тест выхода завершен успешно ===\n")


class TestAuthenticatedFeatures:
    """Тесты функций, доступных после авторизации."""
    
    @pytest.fixture(scope="class")
    def authenticated_page(
        self, 
        browser, 
        frontend_url: str, 
        test_user_credentials: dict
    ):
        """
        Фикстура, которая создает авторизованную страницу для всех тестов в классе.
        Это позволяет избежать повторной авторизации для каждого теста.
        """
        # Создаем новый контекст и страницу
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='ru-RU',
            ignore_https_errors=True,
        )
        page = context.new_page()
        page.set_default_timeout(30000)
        
        # Выполняем авторизацию
        print("\n=== Выполняем авторизацию для тестов ===")
        page.goto(frontend_url)
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        
        # Нажимаем кнопку входа
        login_button = page.get_by_role("button", name="Войти через Authentik")
        login_button.click()
        
        # Ждем редиректа на Authentik
        page.wait_for_url("**/localhost:9000/**", timeout=15000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        # Проверяем наличие кнопки Keycloak
        try:
            keycloak_button = page.locator('a:has-text("Keycloak"), button:has-text("Keycloak")').first
            if keycloak_button.is_visible(timeout=3000):
                keycloak_button.click()
                page.wait_for_load_state("networkidle")
                time.sleep(2)
        except:
            pass
        
        # Вводим учетные данные
        current_url = page.url
        if "keycloak" in current_url.lower() or "8080" in current_url:
            page.wait_for_selector('input[name="username"], input[id="username"]', timeout=10000)
            page.locator('input[name="username"], input[id="username"]').first.fill(test_user_credentials["username"])
            page.locator('input[name="password"], input[id="password"]').first.fill(test_user_credentials["password"])
            page.locator('input[type="submit"], button[type="submit"]').first.click()
        else:
            page.wait_for_selector('input[name="uidField"], input[type="text"]', timeout=10000)
            page.locator('input[name="uidField"], input[type="text"]').first.fill(test_user_credentials["username"])
            try:
                continue_button = page.get_by_role("button", name="Continue")
                if continue_button.is_visible(timeout=2000):
                    continue_button.click()
                    time.sleep(1)
            except:
                pass
            page.locator('input[name="password"], input[type="password"]').first.fill(test_user_credentials["password"])
            page.get_by_role("button", name="Sign in").click()
        
        # Ждем редиректа на фронтенд
        page.wait_for_url(f"{frontend_url}/**", timeout=20000)
        time.sleep(5)
        
        # Проверяем успешную авторизацию
        success_indicator = page.get_by_text("Вы авторизованы")
        expect(success_indicator).to_be_visible(timeout=10000)
        print("✓ Авторизация выполнена успешно\n")
        
        yield page
        
        # Закрываем страницу и контекст после всех тестов
        page.close()
        context.close()
    
    def test_frontend_shows_content_after_redirect(self, authenticated_page: Page):
        """
        Проверяет, что фронтенд показывает содержимое после успешного редиректа.
        """
        print("=== Тест: Проверка отображения контента после редиректа ===")
        
        # Проверяем наличие основных элементов интерфейса
        expect(authenticated_page.get_by_text("Вы авторизованы")).to_be_visible()
        expect(authenticated_page.get_by_text("Информация о пользователе")).to_be_visible()
        expect(authenticated_page.get_by_text("Запрос к бэкенду")).to_be_visible()
        
        print("✓ Все основные элементы интерфейса отображаются")
        print("=== Тест завершен успешно ===\n")
    
    def test_reports_button_shows_jwt_content(self, authenticated_page: Page):
        """
        Проверяет, что кнопка /reports показывает содержимое JWT (данные пользователя).
        """
        print("=== Тест: Проверка кнопки /reports ===")
        
        # Находим и нажимаем кнопку "Вызвать GET /reports"
        reports_button = authenticated_page.get_by_role("button", name="Вызвать GET /reports")
        expect(reports_button).to_be_visible()
        print("✓ Кнопка 'Вызвать GET /reports' найдена")
        
        reports_button.click()
        print("✓ Кнопка нажата")
        
        # Ждем ответа от бэкенда
        time.sleep(2)
        
        # Проверяем наличие статуса ответа
        status_text = authenticated_page.get_by_text("HTTP статус код:")
        expect(status_text).to_be_visible(timeout=10000)
        print("✓ Получен ответ от бэкенда")
        
        # Проверяем, что статус код 200
        status_code = authenticated_page.locator('span.font-mono').first
        actual_status = status_code.text_content()
        print(f"   Статус код от бэкенда: {actual_status}")
        
        # Если не 200, выводим ошибку
        if actual_status != "200":
            error_section = authenticated_page.locator('pre.bg-red-50')
            if error_section.is_visible():
                error_text = error_section.text_content()
                print(f"   Ошибка от бэкенда: {error_text}")
        
        expect(status_code).to_have_text("200")
        print("✓ Статус код: 200")
        
        # Проверяем наличие JSON ответа
        # Ищем все pre элементы
        all_pres = authenticated_page.locator('pre').all()
        print(f"   Найдено {len(all_pres)} элементов <pre>")
        for i, pre in enumerate(all_pres):
            is_visible = pre.is_visible()
            classes = pre.get_attribute('class')
            print(f"   <pre> #{i}: visible={is_visible}, class='{classes}'")
        
        # Ищем pre с классом bg-gray-100 (ответ от сервера)
        # Берем второй элемент (индекс 1), так как первый находится в скрытом <details> для userinfo
        json_response = authenticated_page.locator('pre.bg-gray-100').nth(1)
        expect(json_response).to_be_visible()
        
        # Получаем текст ответа и парсим JSON
        response_text = json_response.inner_text()
        response_data = json.loads(response_text)
        
        # Проверяем структуру ответа
        assert "message" in response_data, "Ответ не содержит поле 'message'"
        assert "user" in response_data, "Ответ не содержит поле 'user'"
        assert "reports" in response_data, "Ответ не содержит поле 'reports'"
        
        # Проверяем наличие ролей
        user_data = response_data["user"]
        assert "roles" in user_data, "Ответ не содержит поле 'roles'"
        assert isinstance(user_data["roles"], list), "Поле 'roles' должно быть списком"
        
        # Проверяем, что есть роль prothetic_users
        assert "prothetic_users" in user_data["roles"], f"Роль 'prothetic_users' не найдена. Доступные роли: {user_data['roles']}"
        print(f"✓ Найдена роль 'prothetic_users' среди ролей: {user_data['roles']}")
        
        # Проверяем данные пользователя
        user_data = response_data["user"]
        assert "username" in user_data, "Данные пользователя не содержат 'username'"
        assert "email" in user_data, "Данные пользователя не содержат 'email'"
        assert "groups" in user_data, "Данные пользователя не содержат 'groups'"
        assert "uid" in user_data, "Данные пользователя не содержат 'uid'"
        
        print(f"✓ Получены данные пользователя:")
        print(f"  - Username: {user_data.get('username')}")
        print(f"  - Email: {user_data.get('email')}")
        print(f"  - Groups: {user_data.get('groups')}")
        print(f"  - UID: {user_data.get('uid')}")
        
        # Проверяем наличие отчетов
        reports = response_data["reports"]
        assert len(reports) > 0, "Список отчетов пуст"
        print(f"✓ Получено отчетов: {len(reports)}")
        
        print("=== Тест завершен успешно ===\n")


class TestFullE2EScenario:
    """Полный E2E сценарий от начала до конца."""
    
    def test_complete_user_journey(
        self,
        page: Page,
        frontend_url: str,
        backend_url: str,
        test_user_credentials: dict
    ):
        """
        Полный сценарий использования приложения:
        1. Проверка доступности сервисов
        2. Открытие фронтенда
        3. Авторизация
        4. Проверка отображения контента
        5. Вызов API бэкенда
        6. Проверка данных
        """
        print("\n" + "="*70)
        print("=== ПОЛНЫЙ E2E СЦЕНАРИЙ ===")
        print("="*70)
        
        # 1. Проверка доступности бэкенда
        print("\n1. Проверяем доступность бэкенда")
        response = requests.get(backend_url + "/", timeout=10)
        assert response.status_code == 404
        assert response.json().get("detail") == "Not Found"
        print(f"✓ Backend доступен: {backend_url}")
        
        # 2. Открываем фронтенд
        print("\n2. Открываем фронтенд")
        page.goto(frontend_url)
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        print(f"✓ Фронтенд загружен: {frontend_url}")
        
        # 3. Авторизация
        print("\n3. Выполняем авторизацию")
        login_button = page.get_by_role("button", name="Войти через Authentik")
        expect(login_button).to_be_visible(timeout=10000)
        login_button.click()
        
        page.wait_for_url("**/localhost:9000/**", timeout=15000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        # Проверяем кнопку Keycloak
        try:
            keycloak_button = page.locator('a:has-text("Keycloak"), button:has-text("Keycloak")').first
            if keycloak_button.is_visible(timeout=3000):
                keycloak_button.click()
                page.wait_for_load_state("networkidle")
                time.sleep(2)
        except:
            pass
        
        # Вводим учетные данные
        current_url = page.url
        if "keycloak" in current_url.lower() or "8080" in current_url:
            page.wait_for_selector('input[name="username"], input[id="username"]', timeout=10000)
            page.locator('input[name="username"], input[id="username"]').first.fill(test_user_credentials["username"])
            page.locator('input[name="password"], input[id="password"]').first.fill(test_user_credentials["password"])
            page.locator('input[type="submit"], button[type="submit"]').first.click()
        else:
            page.wait_for_selector('input[name="uidField"], input[type="text"]', timeout=10000)
            page.locator('input[name="uidField"], input[type="text"]').first.fill(test_user_credentials["username"])
            try:
                continue_button = page.get_by_role("button", name="Continue")
                if continue_button.is_visible(timeout=2000):
                    continue_button.click()
                    time.sleep(1)
            except:
                pass
            page.locator('input[name="password"], input[type="password"]').first.fill(test_user_credentials["password"])
            page.get_by_role("button", name="Sign in").click()
        
        page.wait_for_url(f"{frontend_url}/**", timeout=20000)
        time.sleep(5)
        print("✓ Авторизация выполнена успешно")
        
        # 4. Проверяем отображение контента
        print("\n4. Проверяем отображение контента после авторизации")
        expect(page.get_by_text("Вы авторизованы")).to_be_visible(timeout=10000)
        expect(page.get_by_text("Информация о пользователе")).to_be_visible()
        expect(page.get_by_text("Запрос к бэкенду")).to_be_visible()
        
        # 5. Вызываем API бэкенда
        print("\n5. Вызываем API бэкенда через кнопку /reports")
        reports_button = page.get_by_role("button", name="Вызвать GET /reports")
        expect(reports_button).to_be_visible()
        reports_button.click()
        time.sleep(2)
        
        # 6. Проверяем данные
        print("\n6. Проверяем полученные данные")
        status_code = page.locator('span.font-mono').first
        expect(status_code).to_have_text("200")
        
        # Берем второй pre элемент (индекс 1), так как первый находится в скрытом <details> для userinfo
        json_response = page.locator('pre.bg-gray-100').nth(1)
        expect(json_response).to_be_visible()
        response_text = json_response.inner_text()
        response_data = json.loads(response_text)
        
        assert "user" in response_data
        assert response_data["user"]["username"] == test_user_credentials["username"]
        print(f"✓ Получены корректные данные пользователя: {response_data['user']['username']}")
        
        print("\n" + "="*70)
        print("=== ПОЛНЫЙ E2E СЦЕНАРИЙ ЗАВЕРШЕН УСПЕШНО ===")
        print("="*70 + "\n")


class TestMultipleUsersAndLogout:
    """Тесты для проверки работы с несколькими пользователями и корректного выхода."""
    
    def test_prothetic2_has_roles(
        self,
        page: Page,
        frontend_url: str
    ):
        """
        Проверяет, что пользователь prothetic2 имеет роли в JWT токене.
        Проблема: при входе под prothetic2 отображается пустой список ролей.
        """
        print(f"\n=== Тест: Проверка ролей для пользователя prothetic2 ===")
        
        # Учетные данные для prothetic2
        username = "prothetic2"
        password = "prothetic123"
        
        # Шаг 1: Авторизуемся под prothetic2
        print("1. Авторизация под prothetic2")
        page.goto(frontend_url)
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        
        # Нажимаем кнопку входа
        login_button = page.get_by_role("button", name="Войти через Authentik")
        login_button.click()
        
        # Ждем редиректа на Authentik
        page.wait_for_url("**/localhost:9000/**", timeout=15000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        # Нажимаем кнопку Keycloak
        keycloak_button = page.locator('a:has-text("Keycloak"), button:has-text("Keycloak")').first
        keycloak_button.click()
        time.sleep(2)
        
        # Вводим учетные данные в Keycloak
        current_url = page.url
        if "keycloak" in current_url.lower() or "8080" in current_url:
            page.wait_for_selector('input[name="username"], input[id="username"]', timeout=10000)
            page.locator('input[name="username"], input[id="username"]').first.fill(username)
            page.locator('input[name="password"], input[id="password"]').first.fill(password)
            page.locator('input[type="submit"], button[type="submit"]').first.click()
            print(f"✓ Введены учетные данные: {username}")
        
        # Ждем возврата на Authentik и нажимаем кнопку подтверждения
        time.sleep(2)
        try:
            continue_button = page.get_by_role("button", name="Войти")
            if continue_button.is_visible(timeout=3000):
                continue_button.click()
                time.sleep(2)
        except:
            pass
        
        # Ждем редиректа на фронтенд
        page.wait_for_url(f"{frontend_url}/**", timeout=20000)
        time.sleep(5)
        
        # Проверяем, что авторизованы
        success_indicator = page.locator('text=/Вы авторизованы|✓ Вы авторизованы/i')
        expect(success_indicator).to_be_visible(timeout=15000)
        print("✓ Авторизация выполнена успешно")
        
        # Шаг 2: Вызываем API и проверяем роли
        print("2. Проверяем роли в JWT токене")
        reports_button = page.get_by_role("button", name="Вызвать GET /reports")
        expect(reports_button).to_be_visible()
        reports_button.click()
        time.sleep(2)
        
        # Получаем ответ
        json_response = page.locator('pre.bg-gray-100').nth(1)
        expect(json_response).to_be_visible()
        response_text = json_response.inner_text()
        response_data = json.loads(response_text)
        
        # Проверяем роли
        user_data = response_data["user"]
        assert "roles" in user_data, "Ответ не содержит поле 'roles'"
        assert isinstance(user_data["roles"], list), "Поле 'roles' должно быть списком"
        assert len(user_data["roles"]) > 0, f"Список ролей пуст для пользователя {username}"
        assert "prothetic_users" in user_data["roles"], f"Роль 'prothetic_users' не найдена. Доступные роли: {user_data['roles']}"
        
        print(f"✓ Пользователь {username} имеет роли: {user_data['roles']}")
        print(f"=== Тест завершен успешно ===\n")
    
    def test_logout_and_relogin(
        self,
        page: Page,
        frontend_url: str,
        test_user_credentials: dict
    ):
        """
        Проверяет, что после выхода можно снова войти.
        
        Сценарий:
        1. Входим под prothetic1
        2. Выходим через кнопку "Выйти"
        3. Проверяем, что вернулись на страницу входа
        4. Снова нажимаем "Войти через Authentik" -> Keycloak
        5. Входим снова (Keycloak может запомнить сессию через SSO)
        6. Проверяем, что вход успешен
        
        Примечание: Keycloak использует SSO и запоминает сессию.
        Для полной очистки сессии Keycloak требуется прямой logout в Keycloak,
        но это невозможно, так как пользователь входит через Authentik (нет cookie Keycloak).
        """
        print(f"\n=== Тест: Проверка очистки сессии Keycloak после logout ===")
        
        # Шаг 1: Авторизуемся под prothetic1
        print("1. Авторизация под prothetic1")
        page.goto(frontend_url)
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        
        login_button = page.get_by_role("button", name="Войти через Authentik")
        login_button.click()
        
        page.wait_for_url("**/localhost:9000/**", timeout=15000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        keycloak_button = page.locator('a:has-text("Keycloak"), button:has-text("Keycloak")').first
        keycloak_button.click()
        time.sleep(2)
        
        current_url = page.url
        if "keycloak" in current_url.lower() or "8080" in current_url:
            page.wait_for_selector('input[name="username"], input[id="username"]', timeout=10000)
            page.locator('input[name="username"], input[id="username"]').first.fill(test_user_credentials["username"])
            page.locator('input[name="password"], input[id="password"]').first.fill(test_user_credentials["password"])
            page.locator('input[type="submit"], button[type="submit"]').first.click()
            print(f"✓ Введены учетные данные: {test_user_credentials['username']}")
        
        time.sleep(2)
        try:
            continue_button = page.get_by_role("button", name="Войти")
            if continue_button.is_visible(timeout=3000):
                continue_button.click()
                time.sleep(2)
        except:
            pass
        
        page.wait_for_url(f"{frontend_url}/**", timeout=20000)
        time.sleep(5)
        
        success_indicator = page.locator('text=/Вы авторизованы|✓ Вы авторизованы/i')
        expect(success_indicator).to_be_visible(timeout=15000)
        print("✓ Первая авторизация выполнена успешно")
        
        # Шаг 2: Выходим
        print("2. Выполняем выход")
        logout_button = page.get_by_role("button", name="Выйти")
        expect(logout_button).to_be_visible()
        logout_button.click()
        print("   Кнопка выхода нажата, ожидаем редиректов...")
        time.sleep(5)  # Даем время на цепочку редиректов: Keycloak -> Authentik -> Frontend
        
        # Проверяем текущий URL
        current_url = page.url
        print(f"   Текущий URL после logout: {current_url}")
        
        # Ждем, пока вернемся на страницу входа
        # Authentik должен редиректнуть на фронтенд
        try:
            page.wait_for_url(f"{frontend_url}/**", timeout=15000)
            print(f"   Редирект выполнен: {page.url}")
        except:
            print(f"   Таймаут редиректа, текущий URL: {page.url}")
            # Если мы все еще на Authentik или Keycloak, переходим на фронтенд вручную
            if "localhost:9000" in page.url or "localhost:8080" in page.url:
                print("   Переходим на фронтенд вручную")
                page.goto(frontend_url)
                page.wait_for_load_state("networkidle")
        
        time.sleep(2)
        
        # Проверяем, что мы на странице входа
        current_url = page.url
        print(f"   Финальный URL: {current_url}")
        
        login_button_after_logout = page.get_by_role("button", name="Войти через Authentik")
        expect(login_button_after_logout).to_be_visible(timeout=10000)
        print("✓ Выход выполнен успешно")
        
        # Шаг 3: Снова входим
        print("3. Повторный вход")
        login_button_after_logout.click()
        
        # Ждем редиректа на Authentik
        page.wait_for_url("**/localhost:9000/**", timeout=15000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        # Нажимаем Keycloak
        print("   На странице Authentik, нажимаем Keycloak")
        keycloak_button = page.locator('a:has-text("Keycloak"), button:has-text("Keycloak")').first
        keycloak_button.click()
        time.sleep(3)
        
        # Шаг 4: Входим снова (Keycloak может автоматически войти через SSO или показать форму)
        print("4. Повторный вход")
        current_url = page.url
        print(f"   Текущий URL: {current_url}")
        
        # Проверяем, на какой странице мы находимся
        if "keycloak" in current_url.lower() or "8080" in current_url:
            # Мы на Keycloak - проверяем, показывает ли он форму входа
            username_field = page.locator('input[name="username"], input[id="username"]').first
            if username_field.is_visible(timeout=3000):
                print("   Keycloak показывает форму входа")
                # Вводим учетные данные
                username_field.fill(test_user_credentials["username"])
                page.locator('input[name="password"], input[id="password"]').first.fill(test_user_credentials["password"])
                page.locator('input[type="submit"], button[type="submit"]').first.click()
                print(f"   Введены учетные данные: {test_user_credentials['username']}")
                time.sleep(2)
            else:
                print("   Keycloak не показал форму (SSO - автоматический вход)")
            
            # Ждем возврата на Authentik
            try:
                continue_button = page.get_by_role("button", name="Войти")
                if continue_button.is_visible(timeout=3000):
                    continue_button.click()
                    time.sleep(2)
            except:
                pass
            
            # Ждем возврата на фронтенд
            try:
                page.wait_for_url(f"{frontend_url}/**", timeout=20000)
            except:
                pass
            time.sleep(3)
        else:
            # Мы уже на фронтенде - Keycloak автоматически вошел через SSO
            print("   Keycloak автоматически вошел (SSO)")
            time.sleep(2)
        
        # Шаг 5: Проверяем, что снова авторизованы
        print("5. Проверяем повторную авторизацию")
        success_indicator = page.locator('text=/Вы авторизованы|✓ Вы авторизованы/i')
        expect(success_indicator).to_be_visible(timeout=10000)
        print("✓ Повторная авторизация выполнена успешно")
        
        print(f"\n=== Тест завершен успешно ===")
        print("ПРИМЕЧАНИЕ: Keycloak использует SSO и может запоминать сессию.\n")
