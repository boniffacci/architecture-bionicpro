"""
Unit-тесты для функции init_debezium_schema.

Проверяет, что функция корректно обрабатывает ошибки подключения к ClickHouse.
"""

import pytest
from unittest.mock import patch, MagicMock


def test_init_debezium_schema_raises_on_connection_failure():
    """
    Тест проверяет, что init_debezium_schema выбрасывает RuntimeError
    при невозможности подключиться к ClickHouse.
    """
    from reports_api.main import init_debezium_schema
    
    # Мокаем get_clickhouse_client, чтобы он всегда выбрасывал исключение
    with patch('reports_api.main.get_clickhouse_client') as mock_get_client:
        mock_get_client.side_effect = Exception("Connection refused")
        
        # Проверяем, что функция выбрасывает RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            init_debezium_schema()
        
        # Проверяем, что сообщение об ошибке содержит информацию о проблеме
        assert "Не удалось подключиться к ClickHouse" in str(exc_info.value)
        assert "Connection refused" in str(exc_info.value)


def test_init_debezium_schema_retries_connection():
    """
    Тест проверяет, что init_debezium_schema делает несколько попыток подключения
    перед тем, как выбросить исключение.
    """
    from reports_api.main import init_debezium_schema
    
    # Мокаем get_clickhouse_client, чтобы он всегда выбрасывал исключение
    with patch('reports_api.main.get_clickhouse_client') as mock_get_client:
        mock_get_client.side_effect = Exception("Connection refused")
        
        # Мокаем time.sleep, чтобы тест выполнялся быстрее
        with patch('time.sleep'):
            # Проверяем, что функция выбрасывает RuntimeError
            with pytest.raises(RuntimeError):
                init_debezium_schema()
            
            # Проверяем, что было сделано 30 попыток подключения
            assert mock_get_client.call_count == 30


def test_init_debezium_schema_succeeds_on_retry():
    """
    Тест проверяет, что init_debezium_schema успешно подключается,
    если ClickHouse становится доступным после нескольких попыток.
    """
    from reports_api.main import init_debezium_schema, debezium_schema_initialized
    import reports_api.main as main_module
    
    # Сбрасываем флаг инициализации
    main_module.debezium_schema_initialized = False
    
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
            init_debezium_schema()
            
            # Проверяем, что было сделано 3 попытки
            assert call_count[0] == 3
            
            # Проверяем, что флаг инициализации установлен
            assert main_module.debezium_schema_initialized is True
    
    # Сбрасываем флаг обратно
    main_module.debezium_schema_initialized = False


def test_init_debezium_schema_skips_if_already_initialized():
    """
    Тест проверяет, что init_debezium_schema пропускает инициализацию,
    если она уже была выполнена.
    """
    from reports_api.main import init_debezium_schema
    import reports_api.main as main_module
    
    # Устанавливаем флаг инициализации
    main_module.debezium_schema_initialized = True
    
    # Мокаем get_clickhouse_client
    with patch('reports_api.main.get_clickhouse_client') as mock_get_client:
        # Вызываем функцию
        init_debezium_schema()
        
        # Проверяем, что get_clickhouse_client не вызывался
        mock_get_client.assert_not_called()
    
    # Сбрасываем флаг обратно
    main_module.debezium_schema_initialized = False
