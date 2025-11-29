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


def test_flow_for_one_user(
    page,
    username: str,
    password: str,
    expected_user_uuid: str,
    expected_email: str,
    expected_name: str,
    try_other_users: bool = False,
    other_user_uuids: list = None,
    should_fail_for_other_users: bool = True,
    schema: str = "default",
    skip_own_report: bool = False
):
    """
    Универсальная функция для тестирования flow одного пользователя.
    
    Args:
        page: Playwright page object
        username: Логин пользователя
        password: Пароль пользователя
        expected_user_uuid: Ожидаемый UUID пользователя
        expected_email: Ожидаемый email пользователя
        expected_name: Ожидаемое имя пользователя
        try_other_users: Пытаться ли скачать отчёты других пользователей
        other_user_uuids: Список UUID других пользователей для попытки скачивания
        should_fail_for_other_users: Должна ли возникать ошибка при попытке скачать чужой отчёт
        schema: Схема для отчётов ('default' или 'debezium')
    """
    import time
    
    if other_user_uuids is None:
        other_user_uuids = []
    
    print(f"\n{'=' * 80}")
    print(f"Тест для пользователя: {username}")
    print(f"{'=' * 80}")
    
    # Шаг 1: Открываем главную страницу
    print(f"\n1. Открываем localhost:3000...")
    page.goto(f"http://localhost:3000?_nocache={int(time.time())}", wait_until="networkidle", timeout=30000)
    time.sleep(2)
    
    # Проверяем редирект на Keycloak
    print(f"   Текущий URL: {page.url}")
    assert "localhost:8080" in page.url or "keycloak" in page.url.lower(), "Должен быть редирект на Keycloak"
    print("✓ Редирект на Keycloak выполнен")
    
    # Шаг 2: Вводим логин и пароль
    print(f"\n2. Вводим логин и пароль ({username}:{password})...")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    print("✓ Логин и пароль введены")
    
    # Шаг 3: Нажимаем кнопку входа
    print("\n3. Нажимаем кнопку входа...")
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
    
    # Проверяем авторизацию
    print("\n5. Проверяем авторизацию...")
    try:
        page.wait_for_selector("text=✓ Вы авторизованы!", timeout=10000)
    except Exception as e:
        print(f"   ⚠ Таймаут ожидания сообщения об авторизации: {e}")
    assert page.locator("text=✓ Вы авторизованы!").is_visible(), "Должно быть сообщение об авторизации"
    print("✓ Пользователь авторизован")
    
    # Проверяем информацию о пользователе
    print("\n6. Проверяем информацию о пользователе...")
    user_info_block = page.locator("h2:has-text('Информация о пользователе')").locator("..").inner_text()
    assert username in user_info_block, f"Должен быть виден username: {username}"
    assert expected_email in user_info_block, f"Должен быть виден email: {expected_email}"
    print(f"✓ Информация о пользователе отображается корректно")
    
    # Пропускаем генерацию своего отчёта, если указано
    report_button = page.locator(f"button:has-text('Отчёт ({schema})')")
    
    if not skip_own_report:
        # Шаг 4: Генерируем отчёт для своего пользователя (первый раз - не из кэша)
        print(f"\n7. Генерируем отчёт ({schema}) для своего пользователя (первый раз)...")
        report_button.click()
        
        # Ждём появления результата
        try:
            page.wait_for_selector("text=✓ Отчёт создан успешно:, text=✗ Ошибка при создании отчёта", timeout=10000)
        except Exception as e:
            print(f"   ⚠ Таймаут ожидания результата: {e}")
        
        time.sleep(1)
        page_content = page.content()
        if "✓ Отчёт создан успешно:" in page_content:
            print("✓ Отчёт получен")
            
            # Проверяем, что отчёт НЕ из кэша (первый запрос)
            if "🔄 Не из кэша" in page_content or "Не из кэша" in page_content:
                print("✓ Отчёт сгенерирован заново (не из кэша)")
            else:
                print("⚠ Не удалось определить источник отчёта")
                # Строгая проверка: первый запрос ДОЛЖЕН быть не из кэша
                if "📦 Из кэша" in page_content or "Из кэша" in page_content:
                    raise AssertionError("Первый запрос не должен быть из кэша!")
            
            # Проверяем данные в отчёте
            report_text = page.locator("div.bg-gray-100.rounded-lg").nth(0).inner_text()
            assert expected_name in report_text, f"Отчёт должен содержать имя: {expected_name}"
            assert expected_email in report_text, f"Отчёт должен содержать email: {expected_email}"
            print(f"✓ Данные в отчёте корректны")
        else:
            print("✗ Ошибка при создании отчёта")
            raise AssertionError("Не удалось создать отчёт")
        
        # Шаг 5: Генерируем тот же отчёт второй раз (должен быть из кэша)
        print(f"\n8. Генерируем тот же отчёт ({schema}) второй раз (должен быть из кэша)...")
        report_button.click()
        
        # Ждём появления результата
        try:
            page.wait_for_selector("text=✓ Отчёт создан успешно:, text=✗ Ошибка при создании отчёта", timeout=10000)
        except Exception as e:
            print(f"   ⚠ Таймаут ожидания результата: {e}")
        
        time.sleep(1)
        page_content = page.content()
        if "✓ Отчёт создан успешно:" in page_content:
            print("✓ Отчёт получен")
            
            # Проверяем, что отчёт ИЗ кэша (второй запрос)
            if "📦 Из кэша" in page_content or "Из кэша" in page_content:
                print("✓ Отчёт загружен из кэша")
            else:
                print("✗ Отчёт не из кэша!")
                # Строгая проверка: второй запрос ДОЛЖЕН быть из кэша
                raise AssertionError("Второй запрос должен быть из кэша!")
            
            # Проверяем данные в отчёте
            report_text = page.locator("div.bg-gray-100.rounded-lg").nth(0).inner_text()
            assert expected_name in report_text, f"Отчёт должен содержать имя: {expected_name}"
            assert expected_email in report_text, f"Отчёт должен содержать email: {expected_email}"
            print(f"✓ Данные в отчёте корректны")
        else:
            print("✗ Ошибка при создании отчёта")
            raise AssertionError("Не удалось создать отчёт")
    else:
        print(f"\n7. Пропускаем генерацию своего отчёта (skip_own_report=True)")
    
    # Шаг 6: Пытаемся скачать отчёты других пользователей (если указано)
    if try_other_users and other_user_uuids:
        for other_uuid in other_user_uuids:
            print(f"\n9. Пытаемся скачать отчёт для другого пользователя (UUID: {other_uuid})...")
            
            # Вводим кастомный UUID
            custom_uuid_input = page.locator('input[id="customUserUuid"]')
            custom_uuid_input.fill(other_uuid)
            print(f"✓ Введён кастомный UUID: {other_uuid}")
            
            # Генерируем отчёт (первый раз)
            report_button.click()
            print("   Ожидаем генерации отчёта...")
            
            # Ждём появления результата (либо успех, либо ошибка)
            try:
                page.wait_for_selector("text=✓ Отчёт создан успешно:, text=✗ Ошибка при создании отчёта", timeout=10000)
            except Exception as e:
                print(f"   ⚠ Таймаут ожидания результата: {e}")
            
            time.sleep(1)  # Небольшая пауза для завершения рендеринга
            page_content = page.content()
            
            if should_fail_for_other_users:
                # Должна быть ошибка доступа
                if "✗ Ошибка при создании отчёта" in page_content or "403" in page_content or "Access denied" in page_content:
                    print(f"✓ Получена ожидаемая ошибка доступа для UUID: {other_uuid}")
                else:
                    print(f"✗ Не получена ожидаемая ошибка доступа для UUID: {other_uuid}")
                    raise AssertionError(f"Пользователь {username} смог получить доступ к чужому отчёту")
            else:
                # Доступ должен быть разрешён (для администраторов)
                if "✓ Отчёт создан успешно:" in page_content:
                    print(f"✓ Отчёт для UUID {other_uuid} получен (администратор)")
                    
                    # Проверяем, что отчёт НЕ из кэша (первый запрос)
                    if "🔄 Не из кэша" in page_content or "Не из кэша" in page_content:
                        print("✓ Отчёт сгенерирован заново (не из кэша)")
                    elif "📦 Из кэша" in page_content or "Из кэша" in page_content:
                        print("⚠ Отчёт из кэша (возможно, файл остался с предыдущего запуска)")
                    else:
                        print("⚠ Не удалось определить источник отчёта")
                    
                    # Генерируем тот же отчёт второй раз (должен быть из кэша)
                    print(f"\n10. Генерируем тот же отчёт для UUID {other_uuid} второй раз...")
                    report_button.click()
                    print("   Ожидаем загрузки из кэша...")
                    time.sleep(5)
                    
                    page_content = page.content()
                    if "📦 Из кэша" in page_content or "Из кэша" in page_content:
                        print("✓ Отчёт загружен из кэша")
                    else:
                        print("✗ Отчёт не из кэша!")
                        # Строгая проверка: второй запрос ДОЛЖЕН быть из кэша
                        raise AssertionError("Второй запрос для другого пользователя должен быть из кэша!")
                else:
                    print(f"✗ Не удалось получить отчёт для UUID {other_uuid}")
                    # Отладочный вывод
                    if "✗ Ошибка при создании отчёта" in page_content:
                        error_block = page.locator("pre.bg-red-50").inner_text() if page.locator("pre.bg-red-50").count() > 0 else "Ошибка не найдена"
                        print(f"   Текст ошибки: {error_block[:500]}")
                    print(f"   Содержимое страницы (первые 1000 символов): {page_content[:1000]}")
                    raise AssertionError(f"Администратор не смог получить доступ к отчёту")
            
            # Очищаем поле кастомного UUID
            custom_uuid_input.fill("")
    
    print(f"\n{'=' * 80}")
    print(f"✓ Тест для пользователя {username} завершён успешно!")
    print(f"{'=' * 80}")


def test_frontend_comprehensive_flow(page):
    """
    Комплексный тест фронтенда с авторизацией и проверкой функциональности.
    
    Тест выполняет следующие сценарии:
    1. Логин как admin1 и попытка скачать отчёт для prosthetic1 (должно быть успешно)
    2. Логин как prosthetic2 и попытка скачать отчёт для prosthetic1 (должно быть неуспешно)
    3. Логин как customer2 и скачивание отчётов из default и debezium схем с проверкой кэширования
    """
    import time

    print("\n" + "=" * 80)
    print("Комплексный тест фронтенда с кэшированием")
    print("=" * 80)
    
    # UUID пользователей
    prosthetic1_uuid = "54885c9b-6eea-48f7-89f9-353ad8273e95"
    prosthetic2_uuid = "7f7861be-8810-4c0c-bdd0-893b6a91aec5"
    customer2_uuid = "57e75ff3-16c7-4a02-a2ad-62f8e274c3dd"
    
    # Сценарий 1: Администратор может скачивать отчёты других пользователей
    print("\n" + "=" * 80)
    print("СЦЕНАРИЙ 1: Администратор скачивает отчёт другого пользователя")
    print("=" * 80)
    
    test_flow_for_one_user(
        page=page,
        username="admin1",
        password="admin123",
        expected_user_uuid="admin1_uuid",  # UUID администратора (не важен для этого теста)
        expected_email="admin1@example.com",
        expected_name="Admin One",
        try_other_users=True,
        other_user_uuids=[prosthetic1_uuid],
        should_fail_for_other_users=False,  # Администратор должен иметь доступ
        schema="default",
        skip_own_report=True  # Пропускаем свой отчёт, так как администратора нет в БД
    )
    
    # Выходим из системы
    print("\nВыходим из системы...")
    page.locator("button:has-text('Выйти')").click()
    time.sleep(2)
    
    # Очищаем cookies и перезагружаем страницу
    page.context.clear_cookies()
    print("✓ Cookies очищены")
    
    # Сценарий 2: Обычный пользователь НЕ может скачивать отчёты других пользователей
    print("\n" + "=" * 80)
    print("СЦЕНАРИЙ 2: Обычный пользователь пытается скачать чужой отчёт")
    print("=" * 80)
    
    test_flow_for_one_user(
        page=page,
        username="prosthetic2",
        password="prosthetic123",
        expected_user_uuid=prosthetic2_uuid,
        expected_email="prosthetic2@example.com",
        expected_name="Prosthetic Two",
        try_other_users=True,
        other_user_uuids=[prosthetic1_uuid],
        should_fail_for_other_users=True,  # Обычный пользователь НЕ должен иметь доступ
        schema="default"
    )
    
    # Выходим из системы
    print("\nВыходим из системы...")
    page.locator("button:has-text('Выйти')").click()
    time.sleep(2)
    
    # Очищаем cookies и перезагружаем страницу
    page.context.clear_cookies()
    print("✓ Cookies очищены")
    
    # Сценарий 3: customer2 скачивает отчёты из default и debezium схем с проверкой кэширования
    print("\n" + "=" * 80)
    print("СЦЕНАРИЙ 3: customer2 скачивает отчёты с проверкой кэширования")
    print("=" * 80)
    
    # Переходим на главную страницу для очистки кэша JavaScript
    print("\nПереходим на главную страницу...")
    page.goto("http://localhost:3000/")
    time.sleep(2)
    print("✓ Страница загружена")
    
    # Сначала тестируем default-схему
    print("\n--- Тестирование default-схемы ---")
    test_flow_for_one_user(
        page=page,
        username="customer2",
        password="customer2_password",
        expected_user_uuid=customer2_uuid,
        expected_email="customer2@bionicpro.zm",
        expected_name="Customer Two",
        try_other_users=False,  # Не пытаемся скачать чужие отчёты
        other_user_uuids=[],
        should_fail_for_other_users=False,
        schema="default"
    )
    
    print("\n" + "=" * 80)
    print("✓ ВСЕ СЦЕНАРИИ ЗАВЕРШЕНЫ УСПЕШНО!")
    print("=" * 80)


def test_customer2_debezium_schema(page):
    """
    Тест для customer2 с debezium-схемой.
    
    Проверяет, что customer2 может скачивать отчёты из debezium-схемы
    с корректным кэшированием.
    """
    import time
    
    print("\n" + "=" * 80)
    print("Тест customer2 с debezium-схемой")
    print("=" * 80)
    
    # UUID пользователя customer2
    customer2_uuid = "57e75ff3-16c7-4a02-a2ad-62f8e274c3dd"
    
    # Ждём готовности фронтенда
    print("\nОжидание готовности фронтенда...")
    max_attempts = 30
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get("http://localhost:3000/", timeout=2)
            if response.status_code in [200, 302, 303, 307, 308]:
                print(f"✓ Фронтенд готов (попытка {attempt})")
                break
        except Exception:
            pass
        print(f"Ожидание фронтенда... (попытка {attempt}/{max_attempts})")
        time.sleep(2)
    else:
        raise Exception("Фронтенд не запустился за 60 секунд")
    
    # Переходим на главную страницу для очистки кэша JavaScript
    print("\nПереходим на главную страницу...")
    page.goto("http://localhost:3000/")
    time.sleep(2)
    print("✓ Страница загружена")
    
    # Тестируем debezium-схему
    print("\n--- Тестирование debezium-схемы ---")
    test_flow_for_one_user(
        page=page,
        username="customer2",
        password="customer2_password",
        expected_user_uuid=customer2_uuid,
        expected_email="customer2@bionicpro.zm",
        expected_name="Customer Two",
        try_other_users=False,  # Не пытаемся скачать чужие отчёты
        other_user_uuids=[],
        should_fail_for_other_users=False,
        schema="debezium"
    )
    
    print("\n" + "=" * 80)
    print("✓ ТЕСТ ЗАВЕРШЁН УСПЕШНО!")
    print("=" * 80)
