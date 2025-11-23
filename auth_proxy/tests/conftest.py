"""
Конфигурация pytest для E2E тестов с Playwright.
"""

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright


@pytest.fixture(scope="session")
def browser_type_launch_args():
    """Аргументы запуска браузера."""
    return {
        "headless": True,  # Запуск в headless режиме
        "args": ["--disable-blink-features=AutomationControlled"],  # Отключаем признаки автоматизации
    }


@pytest.fixture(scope="session")
def browser_context_args():
    """Аргументы контекста браузера."""
    return {
        "viewport": {"width": 1920, "height": 1080},  # Размер окна браузера
        "locale": "ru-RU",  # Локаль
    }


@pytest.fixture(scope="session")
def playwright():
    """Фикстура для запуска Playwright."""
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright: Playwright, browser_type_launch_args):
    """Фикстура для создания браузера."""
    browser = playwright.chromium.launch(**browser_type_launch_args)
    yield browser
    browser.close()


@pytest.fixture(scope="function")
def context(browser: Browser, browser_context_args):
    """Фикстура для создания контекста браузера (изолированная сессия)."""
    context = browser.new_context(**browser_context_args)
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext):
    """Фикстура для создания страницы браузера."""
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture(scope="session")
def frontend_url() -> str:
    """УРЛ фронтенд-сервера (через auth_proxy)."""
    return "http://localhost:3000"


@pytest.fixture(scope="session")
def backend_url() -> str:
    """УРЛ бэкенд-сервера."""
    return "http://0.0.0.0:3003"


@pytest.fixture(scope="session")
def auth_proxy_url() -> str:
    """УРЛ auth_proxy сервера."""
    return "http://localhost:3000"


@pytest.fixture(scope="session")
def test_user() -> dict:
    """Тестовый пользователь для авторизации в Keycloak."""
    return {
        "username": "user1",
        "password": "password123",
    }


@pytest.fixture(scope="session")
def test_admin() -> dict:
    """Тестовый администратор для авторизации в Keycloak."""
    return {
        "username": "admin1",
        "password": "admin123",
    }


@pytest.fixture(scope="session")
def test_prosthetic2() -> dict:
    """Тестовый пользователь prosthetic2 для авторизации в Keycloak."""
    return {
        "username": "prosthetic2",
        "password": "prosthetic123",
        "expected_uuid": "7f7861be-8810-4c0c-bdd0-893b6a91aec5",  # UUID из realm-export.json
    }


@pytest.fixture(scope="session")
def test_customer1() -> dict:
    """Тестовый пользователь customer1 для авторизации в Keycloak (LDAP)."""
    return {
        "username": "customer1",
        "password": "customer1_password",  # Пароль из LDAP
        "expected_uuid": "13737288-edf4-4b14-82ad-8590a4d7c306",  # UUID из realm-export.json
    }


@pytest.fixture(scope="session")
def test_customer2() -> dict:
    """Тестовый пользователь customer2 для авторизации в Keycloak (LDAP)."""
    return {
        "username": "customer2",
        "password": "customer2_password",  # Пароль из LDAP
        "expected_uuid": "57e75ff3-16c7-4a02-a2ad-62f8e274c3dd",  # UUID из realm-export.json
    }
