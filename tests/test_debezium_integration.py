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
        ["docker", "compose", "down", "-v"], cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=120
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
        ["docker", "compose", "up", "-d"], cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=120
    )
    print(f"   docker compose up -d завершён (код: {result.returncode})")
    if result.returncode != 0:
        print(f"   stderr: {result.stderr}")
        pytest.fail("Запуск контейнеров завершился с ошибкой")

    # Шаг 4: Ожидание готовности всех контейнеров
    print("\n4. Ожидание готовности контейнеров...")
    wait_for_all_containers_healthy(max_attempts=90, interval=2)

    # Шаг 5: Вызов /populate_base для crm-api (ДО создания коннектора!)
    print("\n5. Вызов /populate_base для crm-api...")
    populate_response = requests.post("http://localhost:3001/populate_base", timeout=30)
    print(f"   Статус: {populate_response.status_code}")
    assert populate_response.status_code == 200, f"populate_base вернул код {populate_response.status_code}"
    populate_data = populate_response.json()
    print(f"   Результат CRM: {populate_data}")

    # Шаг 6: Вызов /populate_base для telemetry-api
    print("\n6. Вызов /populate_base для telemetry-api...")
    populate_response_telemetry = requests.post("http://localhost:3002/populate_base", timeout=30)
    print(f"   Статус: {populate_response_telemetry.status_code}")
    assert (
        populate_response_telemetry.status_code == 200
    ), f"populate_base telemetry вернул код {populate_response_telemetry.status_code}"
    populate_data_telemetry = populate_response_telemetry.json()
    print(f"   Результат Telemetry: {populate_data_telemetry}")

    # Шаг 7: Ожидание автоматической инициализации Debezium-коннекторов и экспорта данных
    print("\n7. Ожидание автоматической инициализации коннекторов и экспорта данных в Kafka (30 секунд)...")
    print("   (Коннекторы создаются автоматически при старте контейнера debezium)")
    time.sleep(30)

    # Шаг 8: Проверка данных в Kafka для CRM
    print("\n8. Проверка данных CRM в Kafka...")
    check_kafka_data("crm.public.users", "CRM users")

    # Шаг 9: Проверка данных в Kafka для Telemetry
    print("\n9. Проверка данных Telemetry в Kafka...")
    check_kafka_data("telemetry.public.telemetry_events", "Telemetry events")

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


def check_kafka_data(topic_name: str, description: str):
    """
    Проверяет, что данные появились в указанном Kafka-топике.

    Args:
        topic_name: Имя Kafka-топика для проверки
        description: Описание данных для вывода в логах
    """
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
        print(f"\n   Получено сообщений ({description}): {len(messages)}")
        assert len(messages) > 0, f"Не найдено ни одного сообщения в Kafka-топике {topic_name}"

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
                print(f"   Данные записи: {json.dumps(after, indent=2, ensure_ascii=False)[:300]}")
                # Проверяем, что есть поле id
                assert "id" in after, "В данных отсутствует поле id"

        print(f"   ✓ Данные {description} успешно экспортированы в Kafka (найдено {len(messages)} сообщений)")

    except KafkaError as e:
        pytest.fail(f"Ошибка при работе с Kafka ({description}): {e}")
    except Exception as e:
        pytest.fail(f"Неожиданная ошибка при проверке данных в Kafka ({description}): {e}")


if __name__ == "__main__":
    # Можно запустить тест напрямую
    test_debezium_cdc_integration()
