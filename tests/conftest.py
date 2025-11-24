"""Конфигурация pytest для интеграционных тестов."""

import subprocess
import time
import pytest
import requests
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

# Определяем корневую директорию проекта
PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="session", autouse=True)
def docker_compose_setup():
    """
    Фикстура для подготовки Docker Compose окружения.
    Выполняется один раз перед всеми тестами в сессии.
    
    Примечание: Если контейнеры уже запущены, фикстура просто проверит их готовность.
    Для полного перезапуска установите переменную окружения REBUILD_DOCKER=1
    """
    import os
    
    rebuild = os.getenv("REBUILD_DOCKER", "0") == "1"
    
    print("\n" + "=" * 80)
    print("Подготовка Docker Compose окружения...")
    print("=" * 80)
    
    if rebuild:
        # Останавливаем и удаляем существующие контейнеры и volumes
        print("\n1. Остановка существующих контейнеров...")
        subprocess.run(
            ["docker", "compose", "down", "-v"],
            cwd=str(PROJECT_ROOT),
            check=False
        )
        
        # Собираем образы
        print("\n2. Сборка Docker-образов...")
        result = subprocess.run(
            ["docker", "compose", "build"],
            cwd=str(PROJECT_ROOT),
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Сборка завершена (код выхода: {result.returncode})")
        
        # Запускаем контейнеры
        print("\n3. Запуск контейнеров...")
        subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=str(PROJECT_ROOT),
            check=True
        )
    else:
        print("\nКонтейнеры уже запущены, пропускаем перезапуск")
        print("(Для полного перезапуска установите REBUILD_DOCKER=1)")
    
    # Ждём, пока все сервисы станут здоровыми
    print("\nОжидание готовности сервисов...")
    wait_for_services()
    
    print("\n" + "=" * 80)
    print("Docker Compose окружение готово!")
    print("=" * 80 + "\n")
    
    yield
    
    # После всех тестов можно оставить контейнеры запущенными для отладки
    # или остановить их, раскомментировав строки ниже:
    # print("\nОстановка контейнеров...")
    # subprocess.run(
    #     ["docker", "compose", "down"],
    #     cwd="/home/felix/Projects/yandex_swa_pro/architecture-bionicpro",
    #     check=False
    # )


def wait_for_services(max_attempts=60, interval=2):
    """
    Ожидает готовности всех критических сервисов.
    
    Args:
        max_attempts: Максимальное количество попыток проверки
        interval: Интервал между попытками в секундах
    """
    services = {
        "CRM API": "http://localhost:3001/health",
        "Telemetry API": "http://localhost:3002/health",
        "Reports API": "http://localhost:3003/",
        "Keycloak": "http://localhost:8080/",
        "MinIO": "http://localhost:9000/minio/health/live",
        "ClickHouse": "http://localhost:8123/ping",
    }
    
    ready_services = set()
    
    for attempt in range(1, max_attempts + 1):
        print(f"\nПопытка {attempt}/{max_attempts}:")
        
        for service_name, url in services.items():
            if service_name in ready_services:
                continue
                
            try:
                response = requests.get(url, timeout=3)
                if response.status_code in [200, 404]:  # 404 для Reports API (нет эндпоинта /)
                    print(f"  ✓ {service_name} готов")
                    ready_services.add(service_name)
                else:
                    print(f"  ✗ {service_name} вернул код {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"  ✗ {service_name} недоступен: {type(e).__name__}")
        
        if len(ready_services) == len(services):
            print(f"\n✓ Все сервисы готовы за {attempt * interval} секунд!")
            return
        
        if attempt < max_attempts:
            time.sleep(interval)
    
    missing = set(services.keys()) - ready_services
    raise TimeoutError(f"Не удалось дождаться готовности сервисов: {missing}")


@pytest.fixture(scope="function")
def page():
    """
    Фикстура для создания Playwright page для тестов фронтенда.
    
    Использует Chromium в headless режиме.
    """
    with sync_playwright() as p:
        # Запускаем браузер в headless режиме
        browser = p.chromium.launch(headless=True)
        
        # Создаём контекст браузера с игнорированием HTTPS ошибок
        # Отключаем кэш, чтобы всегда загружать свежие файлы
        context = browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1920, "height": 1080},
            bypass_csp=True,  # Обходим Content Security Policy
        )
        
        # Создаём новую страницу
        page = context.new_page()
        
        # Отключаем кэш для страницы
        page.route("**/*", lambda route: route.continue_())
        
        yield page
        
        # Закрываем браузер после теста
        context.close()
        browser.close()
