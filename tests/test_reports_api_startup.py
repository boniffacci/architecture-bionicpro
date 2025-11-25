"""
Тесты для проверки корректности запуска reports_api.

Проверяет, что reports_api корректно обрабатывает ошибки при старте,
в частности при недоступности ClickHouse.
"""

import subprocess
import time
import pytest


def test_reports_api_fails_without_clickhouse():
    """
    Тест проверяет, что reports_api падает при старте, если ClickHouse недоступен.
    
    Этот тест:
    1. Останавливает ClickHouse
    2. Пытается запустить reports_api
    3. Проверяет, что контейнер падает с ошибкой
    4. Восстанавливает ClickHouse
    """
    project_dir = "/home/felix/Projects/yandex_swa_pro/architecture-bionicpro"
    
    print("\n" + "=" * 80)
    print("ТЕСТ: Reports API должен падать при недоступности ClickHouse")
    print("=" * 80)
    
    # Шаг 1: Останавливаем ClickHouse
    print("\n1. Останавливаем ClickHouse...")
    subprocess.run(
        ["docker", "compose", "stop", "olap-db"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )
    print("   ✓ ClickHouse остановлен")
    
    try:
        # Шаг 2: Останавливаем reports-api (если запущен)
        print("\n2. Останавливаем reports-api...")
        subprocess.run(
            ["docker", "compose", "stop", "reports-api"],
            cwd=project_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["docker", "compose", "rm", "-f", "reports-api"],
            cwd=project_dir,
            check=True,
            capture_output=True
        )
        print("   ✓ reports-api остановлен и удалён")
        
        # Шаг 3: Пытаемся запустить reports-api
        print("\n3. Пытаемся запустить reports-api без ClickHouse...")
        subprocess.run(
            ["docker", "compose", "up", "-d", "reports-api"],
            cwd=project_dir,
            check=True,
            capture_output=True
        )
        
        # Ждём некоторое время, чтобы контейнер попытался запуститься
        print("   Ожидание 10 секунд для попытки запуска...")
        time.sleep(10)
        
        # Шаг 4: Проверяем статус контейнера
        print("\n4. Проверяем статус контейнера reports-api...")
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json", "reports-api"],
            cwd=project_dir,
            check=True,
            capture_output=True,
            text=True
        )
        
        import json
        container_info = json.loads(result.stdout.strip())
        container_state = container_info.get("State", "")
        
        print(f"   Статус контейнера: {container_state}")
        
        # Проверяем логи
        print("\n5. Проверяем логи reports-api...")
        logs_result = subprocess.run(
            ["docker", "compose", "logs", "reports-api", "--tail=50"],
            cwd=project_dir,
            check=True,
            capture_output=True,
            text=True
        )
        
        logs = logs_result.stdout
        print("   Последние строки логов:")
        for line in logs.split('\n')[-10:]:
            if line.strip():
                print(f"   {line}")
        
        # Проверяем, что в логах есть ошибка о недоступности ClickHouse
        assert "Не удалось подключиться к ClickHouse" in logs or "Connection refused" in logs, \
            "В логах должна быть ошибка о недоступности ClickHouse"
        
        # Проверяем, что контейнер не в статусе running
        # (может быть exited, restarting и т.д.)
        assert container_state != "running", \
            f"Контейнер reports-api не должен быть в статусе running при недоступности ClickHouse, текущий статус: {container_state}"
        
        print("\n   ✓ Контейнер корректно упал при недоступности ClickHouse")
        
    finally:
        # Шаг 6: Восстанавливаем ClickHouse и reports-api
        print("\n6. Восстанавливаем ClickHouse и reports-api...")
        subprocess.run(
            ["docker", "compose", "up", "-d", "olap-db"],
            cwd=project_dir,
            check=True,
            capture_output=True
        )
        
        # Ждём готовности ClickHouse
        print("   Ожидание готовности ClickHouse...")
        for i in range(30):
            result = subprocess.run(
                ["docker", "compose", "exec", "-T", "olap-db", 
                 "clickhouse-client", "--password=clickhouse_password", "--query=SELECT 1"],
                cwd=project_dir,
                capture_output=True
            )
            if result.returncode == 0:
                print(f"   ✓ ClickHouse готов (попытка {i+1})")
                break
            time.sleep(2)
        
        # Перезапускаем reports-api
        subprocess.run(
            ["docker", "compose", "up", "-d", "reports-api"],
            cwd=project_dir,
            check=True,
            capture_output=True
        )
        
        print("   ✓ ClickHouse и reports-api восстановлены")
    
    print("\n" + "=" * 80)
    print("✓ ТЕСТ ПРОЙДЕН")
    print("=" * 80)


if __name__ == "__main__":
    test_reports_api_fails_without_clickhouse()
