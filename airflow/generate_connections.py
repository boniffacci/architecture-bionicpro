#!/usr/bin/env python3
"""
Генерирует connections.json из переменных окружения
"""
import os
import json

def generate_connections_json():
    """Генерирует connections.json из переменных окружения"""
    
    connections = {
        "postgres": {
            "conn_type": "postgres",
            "host": os.getenv("POSTGRES_HOST"),
            "port": int(os.getenv("POSTGRES_PORT")),    
            "schema": os.getenv("POSTGRES_DB"),
            "login": os.getenv("POSTGRES_USER"),
            "password": os.getenv("POSTGRES_PASSWORD")
        },
        "clickhouse": {
            "conn_type": "http",
            "host": os.getenv("CLICKHOUSE_HOST"),
            "port": int(os.getenv("CLICKHOUSE_PORT")),  # Нативный протокол для clickhouse-driver (порт 9000)
            "login": os.getenv("CLICKHOUSE_USER"),
            "password": os.getenv("CLICKHOUSE_PASSWORD"),
            "extra": json.dumps({
                "database": os.getenv("CLICKHOUSE_DATABASE"),
                "secure": False,
                "verify": False
            })
        }
    }
    
    output_path = "/opt/airflow/connections.json"
    with open(output_path, 'w') as f:
        json.dump(connections, f, indent=2)
    
    print(f"Connections JSON generated at {output_path}")
    print(json.dumps(connections, indent=2))

if __name__ == "__main__":
    generate_connections_json()

