"""
Unit-тесты для функции init_default_schema.

Проверяет, что функция корректно создаёт таблицы в схеме default при запуске reports_api.
"""

import pytest
from unittest.mock import patch, MagicMock


def test_init_default_schema_raises_on_connection_failure():
    """
    Тест проверяет, что init_default_schema выбрасывает RuntimeError
    при невозможности подключиться к ClickHouse.
    """
    from reports_api.main import init_default_schema
    
    # Мокаем get_clickhouse_client, чтобы он всегда выбрасывал исключение
    with patch('reports_api.main.get_clickhouse_client') as mock_get_client:
        mock_get_client.side_effect = Exception("Connection refused")
        
        # Проверяем, что функция выбрасывает RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            init_default_schema()
        
        # Проверяем, что сообщение об ошибке содержит информацию о проблеме
        assert "Не удалось подключиться к ClickHouse" in str(exc_info.value)
        assert "Connection refused" in str(exc_info.value)


def test_init_default_schema_retries_connection():
    """
    Тест проверяет, что init_default_schema делает несколько попыток подключения
    перед тем, как выбросить исключение.
    """
    from reports_api.main import init_default_schema
    
    # Мокаем get_clickhouse_client, чтобы он всегда выбрасывал исключение
    with patch('reports_api.main.get_clickhouse_client') as mock_get_client:
        mock_get_client.side_effect = Exception("Connection refused")
        
        # Мокаем time.sleep, чтобы тест выполнялся быстрее
        with patch('time.sleep'):
            # Проверяем, что функция выбрасывает RuntimeError
            with pytest.raises(RuntimeError):
                init_default_schema()
            
            # Проверяем, что было сделано 30 попыток подключения
            assert mock_get_client.call_count == 30


def test_init_default_schema_succeeds_on_retry():
    """
    Тест проверяет, что init_default_schema успешно подключается,
    если ClickHouse становится доступным после нескольких попыток.
    """
    from reports_api.main import init_default_schema
    
    # Создаём мок клиента
    mock_client = MagicMock()
    mock_client.command = MagicMock()
    mock_client.query = MagicMock(return_value=MagicMock(result_rows=[]))
    
    # Мокаем get_clickhouse_client: первые 2 попытки - ошибка, 3-я - успех
    call_count = [0]
    
    def mock_get_client():
        call_count[0] += 1
        if call_count[0] < 3:
            raise Exception("Connection refused")
        return mock_client
    
    with patch('reports_api.main.get_clickhouse_client', side_effect=mock_get_client):
        # Мокаем time.sleep, чтобы тест выполнялся быстрее
        with patch('time.sleep'):
            # Вызываем функцию - она должна успешно выполниться
            init_default_schema()
            
            # Проверяем, что было сделано 3 попытки
            assert call_count[0] == 3
            
            # Проверяем, что были вызваны команды создания таблиц
            assert mock_client.command.call_count >= 2  # CREATE DATABASE + минимум 1 CREATE TABLE


def test_init_default_schema_creates_users_table():
    """
    Тест проверяет, что init_default_schema создаёт таблицу users,
    если она не существует.
    """
    from reports_api.main import init_default_schema
    
    # Создаём мок клиента
    mock_client = MagicMock()
    mock_client.command = MagicMock()
    # Возвращаем пустой список таблиц (таблицы не существуют)
    mock_client.query = MagicMock(return_value=MagicMock(result_rows=[]))
    
    with patch('reports_api.main.get_clickhouse_client', return_value=mock_client):
        # Вызываем функцию
        init_default_schema()
        
        # Проверяем, что была вызвана команда создания таблицы users
        create_users_called = False
        for call in mock_client.command.call_args_list:
            if 'CREATE TABLE default.users' in str(call):
                create_users_called = True
                break
        
        assert create_users_called, "Команда CREATE TABLE default.users не была вызвана"


def test_init_default_schema_creates_telemetry_events_table():
    """
    Тест проверяет, что init_default_schema создаёт таблицу telemetry_events,
    если она не существует.
    """
    from reports_api.main import init_default_schema
    
    # Создаём мок клиента
    mock_client = MagicMock()
    mock_client.command = MagicMock()
    # Возвращаем пустой список таблиц (таблицы не существуют)
    mock_client.query = MagicMock(return_value=MagicMock(result_rows=[]))
    
    with patch('reports_api.main.get_clickhouse_client', return_value=mock_client):
        # Вызываем функцию
        init_default_schema()
        
        # Проверяем, что была вызвана команда создания таблицы telemetry_events
        create_telemetry_called = False
        for call in mock_client.command.call_args_list:
            if 'CREATE TABLE default.telemetry_events' in str(call):
                create_telemetry_called = True
                break
        
        assert create_telemetry_called, "Команда CREATE TABLE default.telemetry_events не была вызвана"


def test_init_default_schema_skips_existing_tables():
    """
    Тест проверяет, что init_default_schema не пересоздаёт таблицы,
    если они уже существуют.
    """
    from reports_api.main import init_default_schema
    
    # Создаём мок клиента
    mock_client = MagicMock()
    mock_client.command = MagicMock()
    # Возвращаем список существующих таблиц
    mock_client.query = MagicMock(return_value=MagicMock(result_rows=[('users',), ('telemetry_events',)]))
    
    with patch('reports_api.main.get_clickhouse_client', return_value=mock_client):
        # Вызываем функцию
        init_default_schema()
        
        # Проверяем, что команды CREATE TABLE не вызывались
        create_table_calls = 0
        for call in mock_client.command.call_args_list:
            if 'CREATE TABLE default.' in str(call):
                create_table_calls += 1
        
        assert create_table_calls == 0, "Команды CREATE TABLE были вызваны для существующих таблиц"


def test_init_default_schema_creates_only_missing_tables():
    """
    Тест проверяет, что init_default_schema создаёт только отсутствующие таблицы.
    """
    from reports_api.main import init_default_schema
    
    # Создаём мок клиента
    mock_client = MagicMock()
    mock_client.command = MagicMock()
    # Возвращаем список с одной существующей таблицей
    mock_client.query = MagicMock(return_value=MagicMock(result_rows=[('users',)]))
    
    with patch('reports_api.main.get_clickhouse_client', return_value=mock_client):
        # Вызываем функцию
        init_default_schema()
        
        # Проверяем, что была вызвана команда создания только telemetry_events
        create_users_called = False
        create_telemetry_called = False
        
        for call in mock_client.command.call_args_list:
            if 'CREATE TABLE default.users' in str(call):
                create_users_called = True
            if 'CREATE TABLE default.telemetry_events' in str(call):
                create_telemetry_called = True
        
        assert not create_users_called, "Команда CREATE TABLE default.users была вызвана для существующей таблицы"
        assert create_telemetry_called, "Команда CREATE TABLE default.telemetry_events не была вызвана"
