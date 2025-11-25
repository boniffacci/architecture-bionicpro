"""
Интеграционный тест Debezium CDC.

Тест проверяет, что Debezium корректно экспортирует данные из PostgreSQL (crm-db) в Kafka.
"""

import json
import subprocess
import time
from pathlib import Path

import pytest
import requests
from kafka import KafkaConsumer
from kafka.errors import KafkaError


# Корневая директория проекта
PROJECT_ROOT = Path(__file__).parent.parent


# Отключаем автоматическое использование фикстуры docker_compose_setup
pytestmark = pytest.mark.usefixtures()


def test_debezium_cdc_integration():
    """
    Интеграционный тест Debezium CDC:
    1. Останавливает все контейнеры и удаляет volumes (docker compose down -v)
    2. Запускает контейнеры и ждёт, пока все станут healthy (docker compose up -d)
    3. Вызывает /populate_base для crm-api
    4. Ждёт 10 секунд и проверяет, что данные появились в Kafka
    """
    print("\n" + "=" * 80)
    print("ИНТЕГРАЦИОННЫЙ ТЕСТ DEBEZIUM CDC")
    print("=" * 80)

    # Шаг 1: Остановка контейнеров и удаление volumes
    print("\n1. Остановка контейнеров и удаление volumes...")
    result = subprocess.run(
        ["docker", "compose", "down", "-v"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    print(f"   docker compose down -v завершён (код: {result.returncode})")
    if result.stdout:
        print(f"   stdout: {result.stdout[:200]}")
    if result.stderr:
        print(f"   stderr: {result.stderr[:200]}")

    # Даём время на завершение остановки
    time.sleep(5)

    # Шаг 2: Сборка образов (если есть build-секции)
    print("\n2. Сборка Docker-образов...")
    result = subprocess.run(
        ["docker", "compose", "build"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=600,  # 10 минут на сборку
    )
    print(f"   docker compose build завершён (код: {result.returncode})")
    if result.returncode != 0:
        print(f"   stderr: {result.stderr}")
        pytest.fail("Сборка Docker-образов завершилась с ошибкой")

    # Шаг 3: Запуск контейнеров
    print("\n3. Запуск контейнеров...")
    result = subprocess.run(
        ["docker", "compose", "up", "-d"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    print(f"   docker compose up -d завершён (код: {result.returncode})")
    if result.returncode != 0:
        print(f"   stderr: {result.stderr}")
        pytest.fail("Запуск контейнеров завершился с ошибкой")

    # Шаг 4: Ожидание готовности всех контейнеров
    print("\n4. Ожидание готовности контейнеров...")
    wait_for_all_containers_healthy(max_attempts=90, interval=2)

    # Шаг 5: Инициализация Debezium-коннекторов
    print("\n5. Инициализация Debezium-коннекторов...")
    init_debezium_connectors()

    # Шаг 6: Вызов /populate_base для crm-api
    print("\n6. Вызов /populate_base для crm-api...")
    populate_response = requests.post("http://localhost:3001/populate_base", timeout=30)
    print(f"   Статус: {populate_response.status_code}")
    assert populate_response.status_code == 200, f"populate_base вернул код {populate_response.status_code}"
    populate_data = populate_response.json()
    print(f"   Результат: {populate_data}")

    # Шаг 6: Удаление старого коннектора (если существует) и создание нового
    print("\n6. Инициализация Debezium-коннекторов...")
    delete_existing_connector("crm-connector")
    init_debezium_connectors()

    # Шаг 7: Ожидание и проверка данных в Kafka
    print("\n7. Ожидание экспорта данных в Kafka (15 секунд)...")
    time.sleep(15)

    # Шаг 8: Проверка данных в Kafka
    print("\n8. Проверка данных в Kafka...")
    check_kafka_data()

    print("\n" + "=" * 80)
    print("✓ ТЕСТ УСПЕШНО ЗАВЕРШЁН")
    print("=" * 80)


def wait_for_all_containers_healthy(max_attempts: int = 90, interval: int = 2):
    """
    Ожидает, пока все контейнеры станут healthy.

    Args:
        max_attempts: Максимальное количество попыток
        interval: Интервал между попытками (в секундах)
    """
    services = {
        "Keycloak": "http://localhost:8080/",
        "CRM DB": "crm-db",
        "Telemetry DB": "telemetry-db",
        "CRM API": "http://localhost:3001/health",
        "Telemetry API": "http://localhost:3002/health",
        "Reports API": "http://localhost:3003/",
        "ClickHouse": "http://localhost:8123/ping",
        "MinIO": "http://localhost:9000/minio/health/live",
        "Kafka": "kafka",
        "Debezium": "http://localhost:8083/",
    }

    ready_services = set()

    for attempt in range(1, max_attempts + 1):
        print(f"   Попытка {attempt}/{max_attempts}:")

        for service_name, url_or_container in services.items():
            if service_name in ready_services:
                continue

            # Проверяем health-статус контейнера
            if service_name in ["CRM DB", "Telemetry DB", "Kafka"]:
                if is_container_healthy(url_or_container):
                    print(f"      ✓ {service_name} healthy")
                    ready_services.add(service_name)
                else:
                    print(f"      ✗ {service_name} не healthy")
            else:
                # Проверяем HTTP-эндпоинт
                try:
                    response = requests.get(url_or_container, timeout=3)
                    if response.status_code in [200, 404]:
                        print(f"      ✓ {service_name} готов")
                        ready_services.add(service_name)
                    else:
                        print(f"      ✗ {service_name} вернул код {response.status_code}")
                except requests.exceptions.RequestException:
                    print(f"      ✗ {service_name} недоступен")

        if len(ready_services) == len(services):
            print(f"\n   ✓ Все сервисы готовы за {attempt * interval} секунд!")
            return

        if attempt < max_attempts:
            time.sleep(interval)

    missing = set(services.keys()) - ready_services
    pytest.fail(f"Не удалось дождаться готовности сервисов: {missing}")


def is_container_healthy(container_name: str) -> bool:
    """
    Проверяет, что контейнер имеет статус healthy.

    Args:
        container_name: Имя контейнера

    Returns:
        True если контейнер healthy, False иначе
    """
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format={{.State.Health.Status}}", container_name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            status = result.stdout.strip()
            return status == "healthy"
        return False
    except Exception:
        return False


def delete_existing_connector(connector_name: str):
    """
    Удаляет существующий коннектор (если он существует).

    Args:
        connector_name: Имя коннектора для удаления
    """
    try:
        response = requests.get(f"http://localhost:8083/connectors/{connector_name}", timeout=5)
        if response.status_code == 200:
            print(f"   Удаление существующего коннектора '{connector_name}'...")
            delete_response = requests.delete(
                f"http://localhost:8083/connectors/{connector_name}", timeout=10
            )
            if delete_response.status_code == 204:
                print(f"   ✓ Коннектор '{connector_name}' удалён")
                time.sleep(3)  # Даём время на завершение удаления
            else:
                print(f"   ⚠ Не удалось удалить коннектор: {delete_response.status_code}")
    except requests.exceptions.RequestException:
        print(f"   Коннектор '{connector_name}' не существует")


def init_debezium_connectors():
    """
    Инициализирует Debezium-коннекторы через REST API.
    """
    # Ожидаем, пока Debezium Connect будет готов
    print("   Ожидание готовности Debezium Connect...")
    for i in range(1, 31):
        try:
            response = requests.get("http://localhost:8083/", timeout=5)
            if response.status_code == 200:
                print(f"   ✓ Debezium Connect готов (попытка {i})")
                break
        except requests.exceptions.RequestException:
            pass

        if i < 30:
            print(f"      Ожидание... (попытка {i}/30)")
            time.sleep(2)
    else:
        pytest.fail("Debezium Connect не запустился")

    # Дополнительная пауза для инициализации PostgreSQL
    time.sleep(5)

    # Создаём коннектор для CRM DB
    print("   Создание коннектора для CRM DB...")
    crm_connector_config = {
        "name": "crm-connector",
        "config": {
            "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
            "tasks.max": "1",
            "database.hostname": "crm-db",
            "database.port": "5432",
            "database.user": "debezium_user",
            "database.password": "debezium_password",
            "database.dbname": "crm_db",
            "database.server.name": "crm",
            "topic.prefix": "crm",
            "plugin.name": "pgoutput",
            "slot.name": "debezium_crm",
            "publication.name": "debezium_publication",
            "slot.drop.on.stop": "false",
            "snapshot.mode": "initial",
            "snapshot.fetch.size": "1000",
            "schema.include.list": "public",
            "table.include.list": "public.users",
            "key.converter": "org.apache.kafka.connect.json.JsonConverter",
            "value.converter": "org.apache.kafka.connect.json.JsonConverter",
            "key.converter.schemas.enable": "true",
            "value.converter.schemas.enable": "true",
            "provide.transaction.metadata": "false",
            "time.precision.mode": "adaptive_time_microseconds",
            "decimal.handling.mode": "double",
            "heartbeat.interval.ms": "10000",
            "max.batch.size": "2048",
            "poll.interval.ms": "1000",
            "include.schema.changes": "false",
        },
    }

    try:
        response = requests.post(
            "http://localhost:8083/connectors",
            headers={"Content-Type": "application/json"},
            json=crm_connector_config,
            timeout=10,
        )
        if response.status_code in (200, 201):
            print("   ✓ Коннектор для CRM DB создан")
        elif response.status_code == 409:
            print("   ⚠ Коннектор для CRM DB уже существует")
        else:
            print(f"   ✗ Ошибка создания коннектора: {response.status_code}")
            print(f"   Ответ: {response.text}")
            pytest.fail(f"Не удалось создать коннектор для CRM DB: {response.text}")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Ошибка при создании коннектора: {e}")

    # Ждём инициализации коннектора
    time.sleep(3)

    # Проверяем статус коннектора
    try:
        response = requests.get("http://localhost:8083/connectors/crm-connector/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print(f"   Статус коннектора: {status['connector']['state']}")
            if status["connector"]["state"] != "RUNNING":
                print(f"   ⚠ Коннектор не в состоянии RUNNING: {status}")
        else:
            print(f"   ✗ Не удалось получить статус коннектора: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Ошибка при проверке статуса: {e}")


def check_kafka_data():
    """
    Проверяет, что данные из crm-db появились в Kafka.
    """
    topic_name = "crm.public.users"

    print(f"   Подключение к Kafka и чтение топика '{topic_name}'...")

    try:
        # Создаём Kafka-консьюмер
        consumer = KafkaConsumer(
            topic_name,
            bootstrap_servers=["localhost:9092"],
            auto_offset_reset="earliest",  # Читаем с самого начала
            enable_auto_commit=False,
            consumer_timeout_ms=10000,  # Таймаут 10 секунд
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        # Читаем сообщения
        messages = []
        for message in consumer:
            messages.append(message.value)
            print(f"      Получено сообщение: offset={message.offset}, key={message.key}")

        consumer.close()

        # Проверяем, что данные есть
        print(f"\n   Получено сообщений: {len(messages)}")
        assert len(messages) > 0, "Не найдено ни одного сообщения в Kafka-топике"

        # Проверяем структуру первого сообщения
        if messages:
            first_message = messages[0]
            print(f"   Первое сообщение: {json.dumps(first_message, indent=2, ensure_ascii=False)[:500]}")

            # Проверяем, что сообщение содержит поле 'payload' (структура Debezium)
            assert "payload" in first_message, "Сообщение не содержит поле 'payload'"

            payload = first_message["payload"]
            # Для snapshot-сообщений есть поле 'after' с данными строки
            if "after" in payload:
                after = payload["after"]
                print(f"   Данные пользователя: {json.dumps(after, indent=2, ensure_ascii=False)[:300]}")
                # Проверяем, что есть основные поля таблицы users
                assert "email" in after or "id" in after, "В данных отсутствуют ожидаемые поля"

        print(f"   ✓ Данные успешно экспортированы в Kafka (найдено {len(messages)} сообщений)")

    except KafkaError as e:
        pytest.fail(f"Ошибка при работе с Kafka: {e}")
    except Exception as e:
        pytest.fail(f"Неожиданная ошибка при проверке данных в Kafka: {e}")


if __name__ == "__main__":
    # Можно запустить тест напрямую
    test_debezium_cdc_integration()
