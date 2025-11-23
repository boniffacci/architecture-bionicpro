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
    return "http://0.0.0.0:3002"


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
