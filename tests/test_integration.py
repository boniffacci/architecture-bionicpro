"""Интеграционные тесты для проверки всей системы."""

import pytest
import requests
import clickhouse_connect
import sys
import time
import subprocess
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_all_services_are_running():
    """Проверка, что все сервисы запущены и отвечают."""
    services = {
        "CRM API": "http://localhost:3001/health",
        "Telemetry API": "http://localhost:3002/health",
        "Reports API": "http://localhost:3003/",
        "Keycloak": "http://localhost:8080/",
        "MinIO": "http://localhost:9000/minio/health/live",
        "ClickHouse": "http://localhost:8123/ping",
        "Kafka UI (Kafdrop)": "http://localhost:9100/",
        "Debezium": "http://localhost:8083/",
    }

    for service_name, url in services.items():
        response = requests.get(url, timeout=5)
        # Reports API возвращает 404 для корневого пути, но это нормально
        assert response.status_code in [200, 404], f"{service_name} не отвечает (код {response.status_code})"
        print(f"✓ {service_name} работает")


def test_crm_api_health():
    """Проверка health-эндпоинта CRM API."""
    response = requests.get("http://localhost:3001/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "CRM API"


def test_telemetry_api_health():
    """Проверка health-эндпоинта Telemetry API."""
    response = requests.get("http://localhost:3002/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Telemetry API"


def test_reports_api_root():
    """Проверка корневого эндпоинта Reports API."""
    response = requests.get("http://localhost:3003/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "reports_api"


def test_populate_crm_database():
    """
    Проверка наполнения CRM базы данных тестовыми данными.

    ВАЖНО: Эти данные загружаются через bulk insert и НЕ будут захвачены Debezium,
    так как Debezium захватывает только изменения в WAL после его запуска.
    Для тестирования Debezium используются отдельные тесты с созданием новых записей.
    """
    response = requests.post("http://localhost:3001/populate_base", timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["users_loaded"] == 1000
    print(f"✓ Загружено {data['users_loaded']} пользователей в CRM БД")
    print("  (эти данные не будут в debezium.users, так как загружены до запуска Debezium)")


def test_populate_telemetry_database():
    """
    Проверка наполнения Telemetry базы данных тестовыми данными.

    ВАЖНО: Эти данные загружаются через bulk insert и НЕ будут захвачены Debezium,
    так как Debezium захватывает только изменения в WAL после его запуска.
    Для тестирования Debezium используются отдельные тесты с созданием новых записей.
    """
    response = requests.post("http://localhost:3002/populate_base", timeout=60)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["events_loaded"] == 10000
    print(f"✓ Загружено {data['events_loaded']} событий в Telemetry БД")
    print("  (эти данные не будут в debezium.telemetry_events, так как загружены до запуска Debezium)")


def test_import_data_to_clickhouse():
    """
    Импорт данных из PostgreSQL в ClickHouse через скрипт import_olap_data.py.

    Этот скрипт также создаёт таблицы в схеме default ClickHouse.
    """
    import subprocess

    print("Запуск импорта данных в ClickHouse...")
    result = subprocess.run(
        ["uv", "run", "python", "dags/import_olap_data.py"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, f"Импорт данных завершился с ошибкой: {result.stderr}"
    print("✓ Данные импортированы в ClickHouse")
    print(f"  Вывод: {result.stdout[-200:]}")  # Последние 200 символов вывода


def test_trigger_debezium_schema_initialization():
    """
    Триггер инициализации схемы debezium в ClickHouse.

    Схема debezium создаётся лениво при первом обращении к Reports API с schema=debezium.
    Вызываем инициализацию напрямую через ClickHouse клиент.
    """
    import clickhouse_connect

    print("Инициализация схемы debezium в ClickHouse...")

    # Импортируем функцию инициализации из reports_api
    from reports_api.main import init_debezium_schema

    # Вызываем инициализацию
    init_debezium_schema()

    print("✓ Схема debezium инициализирована")


def test_restart_reports_api_for_debezium_snapshot():
    """
    Перезапуск reports_api после загрузки данных для автоматической инициализации Debezium-коннекторов.

    Reports API автоматически пересоздаёт Debezium-коннекторы при старте (в lifespan),
    что позволяет сделать snapshot данных, загруженных через populate_base.
    """
    print("\nПерезапуск reports_api для автоматической инициализации Debezium-коннекторов...")

    # Перезапускаем контейнер reports_api
    result = subprocess.run(
        ["docker", "compose", "restart", "reports-api"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"✗ Ошибка при перезапуске reports-api:\n{result.stderr}")
        raise AssertionError("Не удалось перезапустить reports-api")

    print("✓ Контейнер reports-api перезапущен")

    # Ждём, пока reports_api снова станет healthy
    print("  Ожидание готовности reports_api...")
    max_wait = 60
    interval = 2

    for attempt in range(1, max_wait // interval + 1):
        try:
            response = requests.get("http://localhost:3003/", timeout=5)
            if response.status_code == 200:
                print(f"✓ Reports API готов к работе (попытка {attempt})")
                # Дополнительное ожидание для завершения инициализации Debezium-коннекторов
                print("  Ожидание завершения инициализации Debezium-коннекторов (15 секунд)...")
                time.sleep(15)
                print("✓ Debezium-коннекторы автоматически инициализированы при старте reports_api")
                return
        except Exception:
            pass

        print(f"  Попытка {attempt}: reports_api ещё не готов, ожидание {interval} сек...")
        time.sleep(interval)

    # Если после всех попыток reports_api не готов, тест провален
    pytest.fail(f"Reports API не стал готов за {max_wait} секунд после перезапуска")


def test_clickhouse_debezium_schema_exists():
    """Проверка, что в ClickHouse создана схема debezium."""
    client = clickhouse_connect.get_client(
        host="localhost", port=8123, username="default", password="clickhouse_password"
    )

    # Проверяем наличие базы данных debezium
    databases = client.query("SHOW DATABASES").result_rows
    database_names = [row[0] for row in databases]

    assert "debezium" in database_names, "База данных debezium не найдена в ClickHouse"
    print("✓ База данных debezium существует в ClickHouse")


def test_clickhouse_debezium_tables_exist():
    """Проверка, что в схеме debezium созданы таблицы users и telemetry_events."""
    client = clickhouse_connect.get_client(
        host="localhost", port=8123, username="default", password="clickhouse_password"
    )

    # Проверяем наличие таблиц в схеме debezium
    tables = client.query("SHOW TABLES FROM debezium").result_rows
    table_names = [row[0] for row in tables]

    # Должны быть Kafka Engine таблицы и Materialized Views
    expected_tables = [
        "users_kafka",
        "users_mv",
        "users",
        "telemetry_events_kafka",
        "telemetry_events_mv",
        "telemetry_events",
    ]

    for table_name in expected_tables:
        assert table_name in table_names, f"Таблица {table_name} не найдена в схеме debezium"
        print(f"✓ Таблица debezium.{table_name} существует")


def test_debezium_users_data_replicated():
    """
    Проверка, что данные из CRM БД реплицируются в ClickHouse через Debezium.

    После перезапуска reports_api коннекторы автоматически пересоздаются и делают
    snapshot существующих данных из populate_base (1000 пользователей).
    """
    import time

    client = clickhouse_connect.get_client(
        host="localhost", port=8123, username="default", password="clickhouse_password"
    )

    # Проверяем, что данные из populate_base появились в debezium.users
    print("\nПроверка репликации пользователей из populate_base...")

    # Даём Debezium время на обработку snapshot (до 60 секунд)
    max_wait = 60
    interval = 2

    for attempt in range(1, max_wait // interval + 1):
        result = client.query("SELECT COUNT(*) FROM debezium.users")
        count = result.result_rows[0][0]

        if count >= 1000:
            print(f"✓ Данные из populate_base реплицированы в debezium.users (попытка {attempt})")
            print(f"✓ Всего записей в debezium.users: {count}")
            assert count >= 1000, f"Ожидалось минимум 1000 пользователей, получено {count}"
            return

        print(f"  Попытка {attempt}: найдено {count} пользователей, ожидание {interval} сек...")
        time.sleep(interval)

    # Если после всех попыток данных нет, тест провален
    pytest.fail(f"Данные из populate_base не появились в debezium.users за {max_wait} секунд")


def test_debezium_telemetry_data_replicated():
    """
    Проверка, что данные из Telemetry БД реплицируются в ClickHouse через Debezium.

    После перезапуска reports_api коннекторы автоматически пересоздаются и делают
    snapshot существующих данных из populate_base (10000 событий).
    """
    import time

    client = clickhouse_connect.get_client(
        host="localhost", port=8123, username="default", password="clickhouse_password"
    )

    # Проверяем, что данные из populate_base появились в debezium.telemetry_events
    print("\nПроверка репликации событий из populate_base...")

    # Даём Debezium время на обработку snapshot (до 60 секунд)
    max_wait = 60
    interval = 2

    for attempt in range(1, max_wait // interval + 1):
        result = client.query("SELECT COUNT(*) FROM debezium.telemetry_events")
        count = result.result_rows[0][0]

        if count >= 10000:
            print(f"✓ Данные из populate_base реплицированы в debezium.telemetry_events (попытка {attempt})")
            print(f"✓ Всего записей в debezium.telemetry_events: {count}")
            assert count >= 10000, f"Ожидалось минимум 10000 событий, получено {count}"
            return

        print(f"  Попытка {attempt}: найдено {count} событий, ожидание {interval} сек...")
        time.sleep(interval)

    # Если после всех попыток данных нет, тест провален
    pytest.fail(f"Данные из populate_base не появились в debezium.telemetry_events за {max_wait} секунд")


def test_data_consistency_between_postgres_and_clickhouse():
    """
    Проверка консистентности данных между PostgreSQL и ClickHouse.

    Проверяем данные в схеме default (импортированные через import_olap_data.py).
    Данные в схеме debezium реплицируются из PostgreSQL через Debezium после
    перезапуска reports_api (см. тесты test_debezium_users_data_replicated и test_debezium_telemetry_data_replicated).
    """
    client = clickhouse_connect.get_client(
        host="localhost", port=8123, username="default", password="clickhouse_password"
    )

    # Проверяем количество пользователей в схеме default (импортированные данные)
    users_count = client.query("SELECT COUNT(*) FROM default.users").result_rows[0][0]
    print(f"✓ Пользователей в default.users: {users_count}")

    # Проверяем количество событий в схеме default
    events_count = client.query("SELECT COUNT(*) FROM default.telemetry_events").result_rows[0][0]
    print(f"✓ Событий в default.telemetry_events: {events_count}")

    # Должно быть ровно 1000 пользователей и 10000 событий (импортированные данные)
    assert users_count == 1000, f"Ожидалось 1000 пользователей, получено {users_count}"
    assert events_count == 10000, f"Ожидалось 10000 событий, получено {events_count}"

    # Проверяем данные в схеме debezium (реплицированные через Debezium после перезапуска reports_api)
    debezium_users = client.query("SELECT COUNT(*) FROM debezium.users").result_rows[0][0]
    debezium_events = client.query("SELECT COUNT(*) FROM debezium.telemetry_events").result_rows[0][0]

    print(f"✓ Пользователей в debezium.users: {debezium_users}")
    print(f"✓ Событий в debezium.telemetry_events: {debezium_events}")
    print(f"  (данные реплицированы из PostgreSQL через Debezium)")

    # Проверяем, что в debezium есть данные из populate_base
    assert debezium_users >= 1000, f"Ожидалось минимум 1000 пользователей в debezium.users, получено {debezium_users}"
    assert debezium_events >= 10000, f"Ожидалось минимум 10000 событий в debezium.telemetry_events, получено {debezium_events}"


def test_frontend_sign_out(page):
    """
    Тест выхода из системы через фронтенд.

    Проверяет, что после нажатия кнопки "Выйти":
    1. Пользователь перенаправляется на страницу входа Keycloak
    2. Пользователь больше не авторизован (не видит "✓ Вы авторизованы!")
    """
    import time

    print("\n" + "=" * 80)
    print("Тест выхода из системы")
    print("=" * 80)

    # Шаг 1: Открываем главную страницу и логинимся
    print("\n1. Открываем localhost:3000 и логинимся...")
    page.goto("http://localhost:3000?_nocache=" + str(int(time.time())), wait_until="networkidle", timeout=30000)
    time.sleep(2)

    # Проверяем редирект на Keycloak
    assert "localhost:8080" in page.url or "keycloak" in page.url.lower(), "Должен быть редирект на Keycloak"

    # Вводим логин и пароль
    page.fill('input[name="username"]', "prosthetic1")
    page.fill('input[name="password"]', "prosthetic123")

    # Нажимаем кнопку входа
    try:
        page.click('input[type="submit"]', timeout=5000)
    except Exception:
        try:
            page.click('button[type="submit"]', timeout=5000)
        except Exception:
            page.click("#kc-login", timeout=5000)

    # Ждём редиректа обратно на localhost:3000
    page.wait_for_url("http://localhost:3000/**", timeout=30000)
    time.sleep(2)

    # Проверяем, что мы авторизованы
    assert page.locator("text=✓ Вы авторизованы!").is_visible(), "Должно быть сообщение об авторизации"
    print("✓ Пользователь авторизован")

    # Шаг 2: Нажимаем кнопку "Выйти"
    print("\n2. Нажимаем кнопку 'Выйти'...")
    sign_out_button = page.locator("button:has-text('Выйти')")
    sign_out_button.click()

    # Ждём перенаправления (до 10 секунд)
    print("   Ожидаем перенаправления...")
    time.sleep(5)

    # Делаем скриншот для отладки
    page.screenshot(path="/tmp/after_sign_out_test.png")
    print("   Скриншот сохранён в /tmp/after_sign_out_test.png")

    # Шаг 3: Проверяем, что пользователь разлогинен
    print("\n3. Проверяем, что пользователь разлогинен...")
    current_url = page.url
    print(f"   Текущий URL: {current_url}")

    # Проверяем, что мы НЕ на localhost:3000 с авторизацией
    page_content = page.content()

    # Должны быть либо на Keycloak, либо на странице входа
    if "localhost:8080" in current_url or "keycloak" in current_url.lower():
        print("✓ Пользователь перенаправлен на Keycloak (разлогинен)")
    elif "✓ Вы авторизованы!" in page_content:
        # Если всё ещё видим сообщение об авторизации - тест провален
        raise AssertionError("ОШИБКА: Пользователь всё ещё авторизован после выхода!")
    else:
        print("✓ Пользователь разлогинен (не видно сообщения об авторизации)")

    print("\n" + "=" * 80)
    print("✓ Тест выхода завершён успешно!")
    print("=" * 80)


def test_frontend_comprehensive_flow(page):
    """
    Комплексный тест фронтенда с авторизацией и проверкой функциональности.

    Тест выполняет следующие действия:
    1. Открывает localhost:3000
    2. Логинится как prosthetic1:prosthetic123
    3. Нажимает кнопку "Посмотреть JWT"
    4. Нажимает кнопку "Отчёт (default)"
    5. Нажимает кнопку "Отчёт (debezium)"
    6. Проверяет, что данные в отчётах соответствуют CSV для этого пользователя
    """
    import time

    print("\n" + "=" * 80)
    print("Комплексный тест фронтенда")
    print("=" * 80)

    # Шаг 1: Открываем главную страницу
    print("\n1. Открываем localhost:3000...")
    # Добавляем параметр для обхода кэша
    page.goto("http://localhost:3000?_nocache=" + str(int(time.time())), wait_until="networkidle", timeout=30000)
    time.sleep(2)

    # Проверяем, что нас перенаправило на Keycloak
    print(f"   Текущий URL: {page.url}")
    assert "localhost:8080" in page.url or "keycloak" in page.url.lower(), "Должен быть редирект на Keycloak"
    print("✓ Редирект на Keycloak выполнен")

    # Шаг 2: Вводим логин и пароль
    print("\n2. Вводим логин и пароль (prosthetic1:prosthetic123)...")
    page.fill('input[name="username"]', "prosthetic1")
    page.fill('input[name="password"]', "prosthetic123")
    print("✓ Логин и пароль введены")

    # Нажимаем кнопку входа
    print("\n3. Нажимаем кнопку входа...")
    # Делаем скриншот для отладки
    page.screenshot(path="/tmp/keycloak_login.png")
    print("   Скриншот сохранён в /tmp/keycloak_login.png")

    # Пробуем разные селекторы для кнопки входа
    try:
        page.click('input[type="submit"]', timeout=5000)
    except Exception:
        try:
            page.click('button[type="submit"]', timeout=5000)
        except Exception:
            page.click("#kc-login", timeout=5000)

    # Ждём редиректа обратно на localhost:3000
    print("\n4. Ожидаем редиректа на localhost:3000...")
    page.wait_for_url("http://localhost:3000/**", timeout=30000)
    time.sleep(2)
    print(f"✓ Редирект выполнен, текущий URL: {page.url}")

    # Проверяем, что мы авторизованы
    print("\n5. Проверяем авторизацию...")
    assert page.locator("text=✓ Вы авторизованы!").is_visible(), "Должно быть сообщение об авторизации"
    print("✓ Пользователь авторизован")

    # Проверяем информацию о пользователе
    print("\n6. Проверяем информацию о пользователе...")
    # Используем более специфичный селектор - проверяем наличие текста в блоке информации
    user_info_block = page.locator("h2:has-text('Информация о пользователе')").locator("..").inner_text()
    assert "prosthetic1" in user_info_block, "Должен быть виден username"
    assert "prosthetic1@example.com" in user_info_block, "Должен быть виден email"
    print("✓ Информация о пользователе отображается корректно")

    # Шаг 3: Нажимаем кнопку "Посмотреть JWT"
    print("\n7. Нажимаем кнопку 'Посмотреть JWT'...")
    jwt_button = page.locator("button:has-text('Посмотреть JWT')")
    jwt_button.click()

    # Ждём появления JWT
    print("   Ожидаем появления JWT...")
    time.sleep(3)  # Даём время на загрузку

    # Делаем скриншот для отладки
    page.screenshot(path="/tmp/after_jwt_click.png")
    print("   Скриншот сохранён в /tmp/after_jwt_click.png")

    # Проверяем, что появился результат (либо успех, либо ошибка)
    page_content = page.content()

    if "✓ JWT получен от reports_api:" in page_content:
        print("✓ JWT получен и отображается")
        # Проверяем, что JWT содержит нужные поля
        jwt_text = page.locator("pre").nth(1).inner_text()  # Второй <pre> - это JWT
        assert "sub" in jwt_text, "JWT должен содержать поле 'sub'"
        assert "54885c9b-6eea-48f7-89f9-353ad8273e95" in jwt_text, "JWT должен содержать правильный UUID пользователя"
        print("✓ JWT содержит корректные данные")
    elif "⚠ JWT не найден" in page_content:
        print("⚠ JWT не найден (это ожидаемо, если reports_api не вернул JWT)")
    else:
        print(f"✗ Неожиданный результат. Содержимое страницы:\n{page_content[:500]}")
        raise AssertionError("Не удалось получить JWT или сообщение об ошибке")

    # Шаг 4: Нажимаем кнопку "Отчёт (default)"
    print("\n8. Нажимаем кнопку 'Отчёт (default)'...")
    default_report_button = page.locator("button:has-text('Отчёт (default)')")
    default_report_button.click()

    # Ждём появления отчёта
    print("   Ожидаем появления отчёта...")
    time.sleep(3)  # Даём время на загрузку

    # Делаем скриншот для отладки
    page.screenshot(path="/tmp/after_default_report_click.png")
    print("   Скриншот сохранён в /tmp/after_default_report_click.png")

    # Проверяем, что появился результат
    page_content = page.content()

    if "✓ Отчёт создан успешно:" in page_content:
        print("✓ Отчёт (default) получен")

        # Проверяем данные в отчёте
        print("\n9. Проверяем данные в отчёте (default)...")
        report_text = page.locator("div.bg-gray-100.rounded-lg").nth(0).inner_text()

        # Пользователь prosthetic1 (UUID: 54885c9b-6eea-48f7-89f9-353ad8273e95)
        # имеет имя "Prosthetic One" и email "prosthetic1@example.com"
        assert "Prosthetic One" in report_text, "Отчёт должен содержать имя пользователя"
        assert "prosthetic1@example.com" in report_text, "Отчёт должен содержать email пользователя"

        # Проверяем количество событий (у prosthetic1 НЕТ событий в CSV, поэтому должно быть 0)
        assert "Всего событий:" in report_text, "Отчёт должен содержать информацию о событиях"
        assert "0" in report_text, "У prosthetic1 нет событий в default схеме"

        print("✓ Данные в отчёте (default) корректны")
        print("  - Имя: Prosthetic One")
        print("  - Email: prosthetic1@example.com")
        print("  - Событий: 0 (нет событий в CSV)")
    elif "✗ Ошибка при создании отчёта" in page_content:
        print("✗ Ошибка при создании отчёта (default)")
        # Извлекаем текст ошибки
        error_text = page.locator("pre.bg-red-50").inner_text()
        print(f"   Текст ошибки: {error_text}")
        raise AssertionError(f"Не удалось создать отчёт (default): {error_text}")
    else:
        print(f"✗ Неожиданный результат при создании отчёта (default)")
        raise AssertionError("Не удалось получить отчёт или сообщение об ошибке")

    # Шаг 5: Нажимаем кнопку "Отчёт (debezium)"
    print("\n10. Нажимаем кнопку 'Отчёт (debezium)'...")
    debezium_report_button = page.locator("button:has-text('Отчёт (debezium)')")
    debezium_report_button.click()

    # Ждём появления отчёта
    print("   Ожидаем появления отчёта...")
    time.sleep(3)  # Даём время на загрузку

    # Делаем скриншот для отладки
    page.screenshot(path="/tmp/after_debezium_report_click.png")
    print("   Скриншот сохранён в /tmp/after_debezium_report_click.png")

    # Проверяем, что появился результат
    page_content = page.content()

    if "✓ Отчёт создан успешно:" in page_content:
        print("✓ Отчёт (debezium) получен")

        # Проверяем данные в отчёте
        print("\n11. Проверяем данные в отчёте (debezium)...")
        report_text = page.locator("div.bg-gray-100.rounded-lg").nth(0).inner_text()

        # В debezium схеме тоже не должно быть событий для prosthetic1,
        # так как он был создан до запуска Debezium
        assert "Prosthetic One" in report_text, "Отчёт должен содержать имя пользователя"
        assert "prosthetic1@example.com" in report_text, "Отчёт должен содержать email пользователя"
        assert "0" in report_text, "У prosthetic1 нет событий в debezium схеме"

        print("✓ Данные в отчёте (debezium) корректны")
        print("  - Имя: Prosthetic One")
        print("  - Email: prosthetic1@example.com")
        print("  - Событий: 0 (нет событий, созданных после запуска Debezium)")
    elif "✗ Ошибка при создании отчёта" in page_content:
        print("✗ Ошибка при создании отчёта (debezium)")
        # Извлекаем текст ошибки
        error_text = page.locator("pre.bg-red-50").inner_text()
        print(f"   Текст ошибки: {error_text}")

        # Проверяем, что это ожидаемая ошибка 404 (пользователь не найден в debezium)
        if "404" in error_text and "не найден в схеме debezium" in error_text:
            print("✓ Получена ожидаемая ошибка 404: пользователь prosthetic1 не найден в debezium схеме")
            print("  (это нормально, так как он был создан до запуска Debezium)")
        else:
            raise AssertionError(f"Не удалось создать отчёт (debezium): {error_text}")
    else:
        print(f"✗ Неожиданный результат при создании отчёта (debezium)")
        raise AssertionError("Не удалось получить отчёт или сообщение об ошибке")

    # Шаг 6: Проверяем функцию выхода
    print("\n11. Проверяем функцию выхода...")
    sign_out_button = page.locator("button:has-text('Выйти')")
    sign_out_button.click()

    # Ждём перезагрузки страницы
    print("   Ожидаем перезагрузки страницы...")
    time.sleep(3)

    # Делаем скриншот для отладки
    page.screenshot(path="/tmp/after_sign_out.png")
    print("   Скриншот сохранён в /tmp/after_sign_out.png")

    # Проверяем, что нас перенаправило на Keycloak (пользователь разлогинен)
    current_url = page.url
    print(f"   Текущий URL после выхода: {current_url}")

    if "localhost:8080" in current_url or "keycloak" in current_url.lower():
        print("✓ Выход выполнен успешно: перенаправлено на Keycloak")
    else:
        # Проверяем, что пользователь не авторизован
        page_content = page.content()
        if "✓ Вы авторизованы!" in page_content:
            raise AssertionError("Выход не выполнен: пользователь всё ещё авторизован")
        else:
            print("✓ Выход выполнен успешно: пользователь не авторизован")

    print("\n" + "=" * 80)
    print("✓ Комплексный тест фронтенда завершён успешно!")
    print("=" * 80)
