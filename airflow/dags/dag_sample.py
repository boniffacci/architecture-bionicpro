from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime

import pandas as pd

import clickhouse_connect
import csv
import psycopg2


TELEMETRY_CSV_FILE_PATH = 'sample_files/telemetry_data.csv'
CRM_DATA_CSV_FILE_PATH = 'sample_files/crm_data.csv'

DEFAULT_ARGS = {
    'owner': 'airflow',
    'start_date': datetime(2025, 10, 1),
}

PG_CRM_CONN = {
    "host": "crm-db",
    "dbname": "crm_db",
    "user": "crm_user",
    "password": "crm_password",
    "port": 5432,
}

CLICKHOUSE_CONN = {
    "host": "report-db",
    "port": 8123,
    "database": "analytic",
    "username": "analytic_user",
    "password": "analytic_password",
}


def _extract_from_postgres(query: str):
    conn = psycopg2.connect(**PG_CRM_CONN)
    cur = conn.cursor()
    cur.execute(query)

    cols = [desc[0] for desc in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    cur.close()
    conn.close()

    return rows


def load_crm_table_data(**context):
    print(f"extracting data from crm table")
    rows = _extract_from_postgres(
        f"""
            SELECT  u.id AS user_id,
                    u.username,
                    u.age,
                    s.prosthesis_id,
                    s.sensor_name,
                    s.sensor_type,
                    s.installed_at
            FROM sensor_to_user stu
            LEFT JOIN users u ON u.id = stu.user_id
            LEFT JOIN sensors s ON s.id = stu.sensor_id
            GROUP BY u.id, s.id
        """
    )

    return rows


def load_telemetry_table_data(**context):
    print(f"extracting data from telemetry table")
    rows = _extract_from_postgres(
        f"""
            SELECT  pm.metric_id,
                    pm.prosthesis_id,
                    pm.timestamp AS metric_timestamp,
                    pm.force_newtons,
                    pm.force_direction,
                    pm.acceleration_x,
                    pm.acceleration_y,
                    pm.acceleration_z,
                    pm.temperature_celsius,
                    pm.battery_level_percent
            FROM prosthesis_metrics pm
        """
    )

    return rows


def combine_crm_and_telemetry_data(**context):
    ti = context["ti"]

    user_sensors = ti.xcom_pull(task_ids="load_crm_table_data")
    sensor_metrics = ti.xcom_pull(task_ids="load_telemetry_table_data")

    df_user_sensors = pd.DataFrame(user_sensors)
    df_user_sensors.to_csv('sample_files/extract_user_sensors.csv', index=False)

    df_sensor_metrics = pd.DataFrame(sensor_metrics)
    df_sensor_metrics.to_csv('sample_files/extract_sensor_metrics.csv', index=False)


def create_analytic_reports_table():
    print(f"create reports table if not exists")
    client = clickhouse_connect.get_client(**CLICKHOUSE_CONN)
    client.command(
        f"""
            CREATE TABLE IF NOT EXISTS reports (
                id UInt64,
                username String,
                age UInt16,
                prosthesis_id UInt64,
                sensor_name String,
                sensor_type String,
                installed_at DateTime,
                metric_timestamp DateTime,
                force_newtons UInt32,
                force_direction Decimal,
                acceleration_x UInt32,
                acceleration_y UInt32,
                acceleration_z UInt32,
                temperature_celsius UInt32,
                battery_level_percent UInt32
            )
            ENGINE = MergeTree()
            ORDER BY id
            PRIMARY KEY id;
        """
    )


def insert_common_data_to_analytic(**context):
    print(f"extracting data from reports table")

    df_user_sensors = pd.read_csv('sample_files/extract_user_sensors.csv', index_col='user_id')
    df_sensor_metrics = pd.read_csv('sample_files/extract_sensor_metrics.csv', index_col='metric_id')

    df_merged = df_sensor_metrics.merge(df_user_sensors, on='prosthesis_id', how='inner')
    df_merged.to_csv('sample_files/merged.csv', index=False)

    columns = [
        "username",
        "age",
        "prosthesis_id",
        "sensor_name",
        "sensor_type",
        "installed_at",
        "metric_timestamp",
        "force_newtons",
        "force_direction",
        "acceleration_x",
        "acceleration_y",
        "acceleration_z",
        "temperature_celsius",
        "battery_level_percent",
    ]

    insert_queries = []
    for _, row in df_merged.iterrows():

        metric_timestamp = datetime.strptime(row["metric_timestamp"], '%Y-%m-%d')
        installed_at = datetime.strptime(row["installed_at"], '%Y-%m-%d %H:%M:%S')

        common_row = [
            row["username"],
            row["age"],
            row["prosthesis_id"],
            row["sensor_name"],
            row["sensor_type"],
            installed_at,
            metric_timestamp,
            row["force_newtons"],
            row["force_direction"],
            row["acceleration_x"],
            row["acceleration_y"],
            row["acceleration_z"],
            row["temperature_celsius"],
            row["battery_level_percent"],
        ]
        insert_queries.append(common_row)

    client = clickhouse_connect.get_client(**CLICKHOUSE_CONN)
    client.insert("reports", insert_queries, column_names=columns)
    client.close()


with DAG(
    'bionic_pro_etl_dag',
    default_args=DEFAULT_ARGS,
    schedule_interval='0 2 * * *',
    catchup=False,
    tags=["postgres", "clickhouse", "etl"],
) as dag:


    create_analytic_reports_table_operator = PythonOperator(
        task_id='create_analytic_reports_table',
        python_callable=create_analytic_reports_table
    )

    load_crm_table_data_operator = PythonOperator(
        task_id='load_crm_table_data',
        python_callable=load_crm_table_data,
        provide_context=True,
    )

    load_telemetry_table_data_operator = PythonOperator(
        task_id='load_telemetry_table_data',
        python_callable=load_telemetry_table_data,
        provide_context=True,
    )

    combine_crm_and_telemetry_data_operator = PythonOperator(
        task_id='combine_crm_and_telemetry_data',
        python_callable=combine_crm_and_telemetry_data,
        provide_context=True,
    )

    insert_common_data_to_analytic_operator = PythonOperator(
        task_id='insert_common_data_to_analytic',
        python_callable=insert_common_data_to_analytic,
        provide_context=True,
    )

    create_analytic_reports_table_operator >> insert_common_data_to_analytic_operator
    [load_crm_table_data_operator, load_telemetry_table_data_operator] >> combine_crm_and_telemetry_data_operator >> insert_common_data_to_analytic_operator
