"""Интеграционные тесты для проверки работы Debezium CDC и наполнения таблиц ClickHouse."""

import time
import pytest
import clickhouse_connect
import psycopg2
import requests
from datetime import datetime


# Конфигурация подключений
CLICKHOUSE_CONFIG = {
    'host': 'localhost',
    'port': 8123,
    'username': 'default',
    'password': 'clickhouse_password'
}

CRM_DB_CONFIG = {
    'host': 'localhost',
    'port': 5444,  # Порт из docker-compose.yaml
    'database': 'crm_db',
    'user': 'crm_user',
    'password': 'crm_password'
}

TELEMETRY_DB_CONFIG = {
    'host': 'localhost',
    'port': 5445,  # Порт из docker-compose.yaml
    'database': 'telemetry_db',
    'user': 'telemetry_user',
    'password': 'telemetry_password'
}

DEBEZIUM_API_URL = 'http://localhost:8083'


@pytest.fixture
def clickhouse_client():
    """Фикстура для подключения к ClickHouse."""
    client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    yield client
    client.close()


@pytest.fixture
def crm_db_connection():
    """Фикстура для подключения к CRM DB."""
    conn = psycopg2.connect(**CRM_DB_CONFIG)
    yield conn
    conn.close()


@pytest.fixture
def telemetry_db_connection():
    """Фикстура для подключения к Telemetry DB."""
    conn = psycopg2.connect(**TELEMETRY_DB_CONFIG)
    yield conn
    conn.close()


def test_debezium_is_running():
    """Проверяет, что Debezium Kafka Connect запущен и доступен."""
    response = requests.get(f'{DEBEZIUM_API_URL}/')
    assert response.status_code == 200, "Debezium Kafka Connect недоступен"
    print("✓ Debezium Kafka Connect запущен и доступен")


def test_debezium_connectors_exist():
    """Проверяет, что Debezium-коннекторы созданы."""
    response = requests.get(f'{DEBEZIUM_API_URL}/connectors')
    assert response.status_code == 200, "Не удалось получить список коннекторов"
    
    connectors = response.json()
    assert 'crm-connector' in connectors, "CRM-коннектор не создан"
    assert 'telemetry-connector' in connectors, "Telemetry-коннектор не создан"
    print(f"✓ Debezium-коннекторы созданы: {connectors}")


def test_debezium_connectors_running():
    """Проверяет, что Debezium-коннекторы работают."""
    # Проверяем CRM-коннектор
    response = requests.get(f'{DEBEZIUM_API_URL}/connectors/crm-connector/status')
    assert response.status_code == 200, "Не удалось получить статус CRM-коннектора"
    
    crm_status = response.json()
    assert crm_status['connector']['state'] == 'RUNNING', \
        f"CRM-коннектор не работает: {crm_status['connector']['state']}"
    
    # Проверяем, что есть хотя бы одна задача
    assert len(crm_status['tasks']) > 0, "У CRM-коннектора нет задач"
    assert crm_status['tasks'][0]['state'] == 'RUNNING', \
        f"Задача CRM-коннектора не работает: {crm_status['tasks'][0]['state']}"
    
    print(f"✓ CRM-коннектор работает: {crm_status['connector']['state']}")
    
    # Проверяем Telemetry-коннектор
    response = requests.get(f'{DEBEZIUM_API_URL}/connectors/telemetry-connector/status')
    assert response.status_code == 200, "Не удалось получить статус Telemetry-коннектора"
    
    telemetry_status = response.json()
    assert telemetry_status['connector']['state'] == 'RUNNING', \
        f"Telemetry-коннектор не работает: {telemetry_status['connector']['state']}"
    
    # Проверяем, что есть хотя бы одна задача
    assert len(telemetry_status['tasks']) > 0, "У Telemetry-коннектора нет задач"
    assert telemetry_status['tasks'][0]['state'] == 'RUNNING', \
        f"Задача Telemetry-коннектора не работает: {telemetry_status['tasks'][0]['state']}"
    
    print(f"✓ Telemetry-коннектор работает: {telemetry_status['connector']['state']}")


def test_clickhouse_debezium_schema_exists(clickhouse_client):
    """Проверяет, что схема debezium создана в ClickHouse."""
    databases = clickhouse_client.query("SHOW DATABASES").result_rows
    database_names = [row[0] for row in databases]
    assert 'debezium' in database_names, "Схема debezium не создана в ClickHouse"
    print("✓ Схема debezium существует в ClickHouse")


def test_clickhouse_debezium_tables_exist(clickhouse_client):
    """Проверяет, что все необходимые таблицы созданы в схеме debezium."""
    tables = clickhouse_client.query("SHOW TABLES FROM debezium").result_rows
    table_names = {row[0] for row in tables}
    
    required_tables = {
        'users_kafka',
        'users',
        'users_mv',
        'telemetry_events_kafka',
        'telemetry_events',
        'telemetry_events_mv'
    }
    
    missing_tables = required_tables - table_names
    assert not missing_tables, f"Отсутствуют таблицы: {missing_tables}"
    print(f"✓ Все необходимые таблицы созданы: {table_names}")


def test_postgresql_crm_data_exists(crm_db_connection):
    """Проверяет, что в CRM DB есть данные."""
    cursor = crm_db_connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    cursor.close()
    
    assert count > 0, "В таблице users нет данных"
    print(f"✓ В CRM DB есть {count} пользователей")


def test_postgresql_telemetry_data_exists(telemetry_db_connection):
    """Проверяет, что в Telemetry DB есть данные."""
    cursor = telemetry_db_connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM telemetry_events")
    count = cursor.fetchone()[0]
    cursor.close()
    
    assert count > 0, "В таблице telemetry_events нет данных"
    print(f"✓ В Telemetry DB есть {count} событий")


def test_clickhouse_users_data_replicated(clickhouse_client):
    """Проверяет, что данные из CRM DB реплицированы в ClickHouse."""
    # Ждём до 60 секунд, пока данные реплицируются
    max_attempts = 30
    for attempt in range(max_attempts):
        result = clickhouse_client.query("SELECT count() FROM debezium.users")
        count = result.result_rows[0][0]
        
        if count > 0:
            print(f"✓ В debezium.users реплицировано {count} пользователей (попытка {attempt + 1})")
            
            # Проверяем структуру данных
            sample = clickhouse_client.query("SELECT * FROM debezium.users LIMIT 1")
            if sample.result_rows:
                print(f"  Пример записи: {sample.result_rows[0]}")
            
            return
        
        print(f"  Ожидание репликации данных в debezium.users... (попытка {attempt + 1}/{max_attempts})")
        time.sleep(2)
    
    pytest.fail(f"Данные не реплицировались в debezium.users за {max_attempts * 2} секунд")


def test_clickhouse_telemetry_data_replicated(clickhouse_client):
    """Проверяет, что данные из Telemetry DB реплицированы в ClickHouse."""
    # Ждём до 60 секунд, пока данные реплицируются
    max_attempts = 30
    for attempt in range(max_attempts):
        result = clickhouse_client.query("SELECT count() FROM debezium.telemetry_events")
        count = result.result_rows[0][0]
        
        if count > 0:
            print(f"✓ В debezium.telemetry_events реплицировано {count} событий (попытка {attempt + 1})")
            
            # Проверяем структуру данных
            sample = clickhouse_client.query("SELECT * FROM debezium.telemetry_events LIMIT 1")
            if sample.result_rows:
                print(f"  Пример записи: {sample.result_rows[0]}")
            
            return
        
        print(f"  Ожидание репликации данных в debezium.telemetry_events... (попытка {attempt + 1}/{max_attempts})")
        time.sleep(2)
    
    pytest.fail(f"Данные не реплицировались в debezium.telemetry_events за {max_attempts * 2} секунд")


def test_data_consistency_users(clickhouse_client, crm_db_connection):
    """Проверяет консистентность данных между PostgreSQL и ClickHouse для users."""
    # Получаем количество записей в PostgreSQL
    cursor = crm_db_connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    pg_count = cursor.fetchone()[0]
    cursor.close()
    
    # Получаем количество записей в ClickHouse
    result = clickhouse_client.query("SELECT count() FROM debezium.users")
    ch_count = result.result_rows[0][0]
    
    # Проверяем, что количество записей совпадает (с учётом возможной задержки репликации)
    assert ch_count > 0, "В debezium.users нет данных"
    
    # Допускаем небольшую разницу из-за возможной задержки репликации
    difference = abs(pg_count - ch_count)
    max_difference = max(1, pg_count * 0.01)  # 1% или минимум 1 запись
    
    assert difference <= max_difference, \
        f"Количество записей не совпадает: PostgreSQL={pg_count}, ClickHouse={ch_count}"
    
    print(f"✓ Консистентность данных users: PostgreSQL={pg_count}, ClickHouse={ch_count}")


def test_data_consistency_telemetry(clickhouse_client, telemetry_db_connection):
    """Проверяет консистентность данных между PostgreSQL и ClickHouse для telemetry_events."""
    # Получаем количество записей в PostgreSQL
    cursor = telemetry_db_connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM telemetry_events")
    pg_count = cursor.fetchone()[0]
    cursor.close()
    
    # Получаем количество записей в ClickHouse
    result = clickhouse_client.query("SELECT count() FROM debezium.telemetry_events")
    ch_count = result.result_rows[0][0]
    
    # Проверяем, что количество записей совпадает (с учётом возможной задержки репликации)
    assert ch_count > 0, "В debezium.telemetry_events нет данных"
    
    # Допускаем небольшую разницу из-за возможной задержки репликации
    difference = abs(pg_count - ch_count)
    max_difference = max(1, pg_count * 0.01)  # 1% или минимум 1 запись
    
    assert difference <= max_difference, \
        f"Количество записей не совпадает: PostgreSQL={pg_count}, ClickHouse={ch_count}"
    
    print(f"✓ Консистентность данных telemetry_events: PostgreSQL={pg_count}, ClickHouse={ch_count}")


def test_olap_db_debezium_schema_exists(clickhouse_client):
    """Проверяет, что в olap-db (ClickHouse) существует схема debezium с данными."""
    print("\n" + "=" * 80)
    print("ПРОВЕРКА СХЕМЫ DEBEZIUM В OLAP-DB (ClickHouse)")
    print("=" * 80)
    
    # Ждём небольшое время для стабилизации репликации
    print("\n1. Ожидание стабилизации репликации (5 секунд)...")
    time.sleep(5)
    
    # Проверяем наличие схемы debezium
    print("\n2. Проверка наличия схемы debezium...")
    databases = clickhouse_client.query("SHOW DATABASES").result_rows
    database_names = [row[0] for row in databases]
    assert 'debezium' in database_names, "Схема debezium не существует в olap-db"
    print("   ✓ Схема debezium существует")
    
    # Проверяем наличие таблиц users и telemetry_events
    print("\n3. Проверка наличия таблиц в схеме debezium...")
    tables = clickhouse_client.query("SHOW TABLES FROM debezium").result_rows
    table_names = {row[0] for row in tables}
    
    assert 'users' in table_names, "Таблица debezium.users не существует"
    print("   ✓ Таблица debezium.users существует")
    
    assert 'telemetry_events' in table_names, "Таблица debezium.telemetry_events не существует"
    print("   ✓ Таблица debezium.telemetry_events существует")
    
    # Проверяем наличие данных в таблице users
    print("\n4. Проверка данных в таблице debezium.users...")
    max_attempts = 30
    users_count = 0
    
    for attempt in range(max_attempts):
        result = clickhouse_client.query("SELECT count() FROM debezium.users")
        users_count = result.result_rows[0][0]
        
        if users_count > 0:
            print(f"   ✓ В таблице debezium.users найдено {users_count} записей (попытка {attempt + 1})")
            
            # Показываем пример записи
            sample = clickhouse_client.query("SELECT * FROM debezium.users LIMIT 1")
            if sample.result_rows:
                print(f"   Пример записи: {sample.result_rows[0]}")
            break
        
        print(f"   Ожидание данных в debezium.users... (попытка {attempt + 1}/{max_attempts})")
        time.sleep(2)
    
    assert users_count > 0, "В таблице debezium.users нет данных"
    
    # Проверяем наличие данных в таблице telemetry_events
    print("\n5. Проверка данных в таблице debezium.telemetry_events...")
    telemetry_count = 0
    
    for attempt in range(max_attempts):
        result = clickhouse_client.query("SELECT count() FROM debezium.telemetry_events")
        telemetry_count = result.result_rows[0][0]
        
        if telemetry_count > 0:
            print(f"   ✓ В таблице debezium.telemetry_events найдено {telemetry_count} записей (попытка {attempt + 1})")
            
            # Показываем пример записи
            sample = clickhouse_client.query("SELECT * FROM debezium.telemetry_events LIMIT 1")
            if sample.result_rows:
                print(f"   Пример записи: {sample.result_rows[0]}")
            break
        
        print(f"   Ожидание данных в debezium.telemetry_events... (попытка {attempt + 1}/{max_attempts})")
        time.sleep(2)
    
    assert telemetry_count > 0, "В таблице debezium.telemetry_events нет данных"
    
    print("\n" + "=" * 80)
    print(f"✓ ПРОВЕРКА ЗАВЕРШЕНА УСПЕШНО")
    print(f"  - Схема debezium: существует")
    print(f"  - Таблица users: {users_count} записей")
    print(f"  - Таблица telemetry_events: {telemetry_count} записей")
    print("=" * 80)


def test_insert_new_user_replicates(clickhouse_client, crm_db_connection):
    """Проверяет, что новые записи в PostgreSQL реплицируются в ClickHouse."""
    # Вставляем нового пользователя в PostgreSQL
    cursor = crm_db_connection.cursor()
    test_uuid = f'test-{int(time.time())}'
    test_email = f'test-{int(time.time())}@example.com'
    
    cursor.execute("""
        INSERT INTO users (user_uuid, name, email, registered_at)
        VALUES (%s, %s, %s, NOW())
        RETURNING id
    """, (test_uuid, 'Test User', test_email))
    
    user_id = cursor.fetchone()[0]
    crm_db_connection.commit()
    cursor.close()
    
    print(f"  Вставлен новый пользователь: id={user_id}, uuid={test_uuid}, email={test_email}")
    
    # Ждём репликации (до 30 секунд)
    max_attempts = 15
    for attempt in range(max_attempts):
        result = clickhouse_client.query(
            "SELECT count() FROM debezium.users WHERE user_uuid = {uuid:String}",
            parameters={'uuid': test_uuid}
        )
        count = result.result_rows[0][0]
        
        if count > 0:
            print(f"✓ Новый пользователь реплицирован в ClickHouse (попытка {attempt + 1})")
            
            # Проверяем данные
            user_data = clickhouse_client.query(
                "SELECT * FROM debezium.users WHERE user_uuid = {uuid:String}",
                parameters={'uuid': test_uuid}
            )
            print(f"  Данные в ClickHouse: {user_data.result_rows[0]}")
            
            return
        
        print(f"  Ожидание репликации нового пользователя... (попытка {attempt + 1}/{max_attempts})")
        time.sleep(2)
    
    pytest.fail(f"Новый пользователь не реплицировался в ClickHouse за {max_attempts * 2} секунд")
