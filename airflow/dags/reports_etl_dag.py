from datetime import datetime, timedelta
import os

from airflow import DAG
from airflow.operators.python import PythonOperator
import clickhouse_connect


def load_crm_and_telemetry(**_):
    host = os.getenv("CLICKHOUSE_HOST", "localhost")
    port = int(os.getenv("CLICKHOUSE_PORT", "8123"))
    user = os.getenv("CLICKHOUSE_USER", "default")
    password = os.getenv("CLICKHOUSE_PASSWORD", "")
    database = os.getenv("CLICKHOUSE_DB", "reports")
    client = clickhouse_connect.get_client(host=host, port=port, username=user, password=password, database=database)

    client.command("CREATE DATABASE IF NOT EXISTS reports")
    client.command("CREATE TABLE IF NOT EXISTS user_reports (user_sub String, ts DateTime, metric Float64) ENGINE = MergeTree ORDER BY (user_sub, ts)")
    client.command("CREATE TABLE IF NOT EXISTS load_markers (loaded_from DateTime, loaded_to DateTime) ENGINE = ReplacingMergeTree ORDER BY loaded_to")

    # Заглушка: вставка синтетических данных
    now = datetime.utcnow()
    start = now - timedelta(days=1)
    end = now
    client.command("INSERT INTO user_reports (user_sub, ts, metric) VALUES", [
        {"user_sub": "user1-sub", "ts": now, "metric": 0.7},
        {"user_sub": "user1-sub", "ts": now, "metric": 0.9},
        {"user_sub": "user2-sub", "ts": now, "metric": 0.5},
    ])
    client.command("INSERT INTO load_markers (loaded_from, loaded_to) VALUES", [
        {"loaded_from": start, "loaded_to": end}
    ])


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 0,
}

with DAG(
    dag_id="reports_etl_dag",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval=timedelta(hours=1),
    catchup=False,
) as dag:
    etl_task = PythonOperator(
        task_id="load_crm_and_telemetry",
        python_callable=load_crm_and_telemetry,
    )


