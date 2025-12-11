from datetime import datetime, timedelta
import pandas as pd
import json
from collections import Counter
from io import StringIO
import logging
import csv
from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow_clickhouse_plugin.hooks.clickhouse import ClickHouseHook
from airflow.operators.python_operator import PythonOperator
from helper import xcom_to_df, df_to_xcom, parse_datetime

default_args = {
    'owner': 'data_engineer',
    'depends_on_past': False,
    'start_date': datetime(2025, 4, 12),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'crm_to_clickhouse_mart_dag',
    default_args=default_args,
    description='ETL: CRM + Telemetry → ClickHouse Mart',
    schedule_interval='0 2 * * *',
    catchup=False,
    tags=['etl', 'clickhouse', 'crm'],
)

def extract_users(**kwargs):
    logging.info("Извлечение пользователей из PostgreSQL...")
    postgres_hook = PostgresHook(postgres_conn_id='crm_db_conn')
    df = postgres_hook.get_pandas_df("""
        SELECT id AS user_id, name, email, age, gender, country, address, phone 
        FROM customers;
    """)
    if df.empty:
        raise ValueError("Таблица customers пуста или не существует.")

    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    users_csv = csv_buffer.getvalue()

    kwargs['ti'].xcom_push(key='users_data', value=users_csv)
    logging.info(f"Извлечено {len(df)} пользователей")

extract_users_task = PythonOperator(
    task_id='extract_users_from_postgres',
    python_callable=extract_users,
    dag=dag,
)

def extract_and_aggregate_telemetry(**kwargs):
    logging.info("Извлечение и агрегация телеметрии из ClickHouse")
    clickhouse_hook = ClickHouseHook(clickhouse_conn_id='clickhouse_conn')
    columns = ['user_id', 'prosthesis_type', 'muscle_group', 'signal_frequency', 'signal_duration', 'signal_amplitude', 'signal_time']
    
    query = f"""
        SELECT {", ".join(columns)}
        FROM emg_sensor_data
    """

    try:
        rows = clickhouse_hook.execute(query) 
    except Exception as e:
        logging.error(f"Ошибка при выполнении запроса к ClickHouse: {e}")
        raise

    if not rows:
        logging.warning("Нет данных телеметрии. Создаём пустой DataFrame.")
        telemetry_df = pd.DataFrame(columns=columns)
    else:
        telemetry_df = pd.DataFrame(rows, columns=columns)
        telemetry_df['user_id'] = pd.to_numeric(telemetry_df['user_id'], errors='coerce').fillna(0).astype('int')
        telemetry_df['signal_time'] = pd.to_datetime(telemetry_df['signal_time'], errors='coerce')

    logging.info(f"Извлечено {len(telemetry_df)} записей телеметрии")

    if telemetry_df.empty:
        agg_df = pd.DataFrame(columns=[
            'user_id', 'total_signals', 'avg_signal_duration_sec',
            'avg_signal_amplitude', 'max_frequency', 'last_signal_time', 'muscle_usage_count'
        ])
        logging.info("Нет данных для агрегации — создана пустая таблица.")
    else:
        agg_df = telemetry_df.groupby('user_id').agg({
            'signal_time': ['count', 'max'],
            'signal_duration': 'mean',
            'signal_amplitude': 'mean',
            'signal_frequency': 'max',
            'muscle_group': lambda x: json.dumps(dict(Counter(x.tolist())), ensure_ascii=False)
        }).reset_index()

        agg_df.columns = [
            'user_id',
            'total_signals',
            'last_signal_time',
            'avg_signal_duration_sec',
            'avg_signal_amplitude',
            'max_frequency',
            'muscle_usage_count'
        ]

    defaults = {
        'total_signals': 0,
        'avg_signal_duration_sec': 0.0,
        'avg_signal_amplitude': 0.0,
        'max_frequency': 0.0,
        'last_signal_time': None,
        'muscle_usage_count': '{"unknown": 0}'
    }

    for col, default in defaults.items():
        if col not in agg_df.columns:
            agg_df[col] = default
        elif agg_df[col].isnull().any():
            if isinstance(default, str) or col == 'muscle_usage_count':
                agg_df[col] = agg_df[col].fillna(str(default))
            else:
                agg_df[col] = agg_df[col].fillna(default)

    if 'last_signal_time' in agg_df.columns:
        agg_df['last_signal_time'] = agg_df['last_signal_time'].where(
            pd.notna(agg_df['last_signal_time']), None
        )

    df_to_xcom(agg_df, kwargs['ti'], 'aggregated_telemetry')
    logging.info(f"Агрегировано {len(agg_df)} пользовательских записей")

extract_telemetry_task = PythonOperator(
    task_id='extract_telemetry_from_clickhouse',
    python_callable=extract_and_aggregate_telemetry,
    dag=dag,
)

def join_crm_telemetry(**kwargs):
    logging.info("Объединение CRM и телеметрии...")
    ti = kwargs['ti']

    users_df = xcom_to_df(ti, 'extract_users_from_postgres', 'users_data')
    telemetry_df = xcom_to_df(ti, 'extract_telemetry_from_clickhouse', 'aggregated_telemetry')

    mart_df = pd.merge(users_df, telemetry_df, on='user_id', how='left')

    fill_values = {
        'total_signals': 0,
        'avg_signal_duration_sec': 0.0,
        'avg_signal_amplitude': 0.0,
        'max_frequency': 0,
        'muscle_usage_count': '{"unknown": 0}',
        'last_signal_time': pd.NaT
    }
    mart_df.fillna(value=fill_values, inplace=True)

    mart_df['user_id'] = mart_df['user_id'].astype('int32')
    mart_df['total_signals'] = mart_df['total_signals'].astype('int32')
    mart_df['avg_signal_duration_sec'] = mart_df['avg_signal_duration_sec'].astype('float32')
    mart_df['avg_signal_amplitude'] = mart_df['avg_signal_amplitude'].astype('float32')
    mart_df['max_frequency'] = mart_df['max_frequency'].astype('int32')

    df_to_xcom(mart_df, ti, 'mart_data')
    logging.info(f"Витрина сформирована: {len(mart_df)} строк")

join_task = PythonOperator(
    task_id='join_crm_with_telemetry',
    python_callable=join_crm_telemetry,
    dag=dag,
)

def create_mart_table(**kwargs):
    logging.info("Создание таблицы витрины в ClickHouse...")
    clickhouse_hook = ClickHouseHook(clickhouse_conn_id='clickhouse_conn')
    logging.info("Удаление старой таблицы...")
    clickhouse_hook.execute("DROP TABLE IF EXISTS report_patient_activity_mart")
    create_sql = """
    CREATE TABLE IF NOT EXISTS report_patient_activity_mart (
        user_id Int32,
        name String,
        age Int32,
        gender String,
        email String,
        country String,
        total_signals Int32,
        avg_signal_duration_sec Float32,
        avg_signal_amplitude Float32,
        max_frequency Int32,
        last_signal_time DateTime,
        muscle_usage_count String
    ) ENGINE = MergeTree()
    ORDER BY (user_id)
    """
    clickhouse_hook.execute(create_sql)
    logging.info("Таблица витрины создана или уже существует")

create_table_task = PythonOperator(
    task_id='create_mart_table',
    python_callable=create_mart_table,
    dag=dag,
)

def load_mart_data(**kwargs):
    logging.info("Загрузка данных в ClickHouse...")
    ti = kwargs['ti']
    mart_csv = ti.xcom_pull(task_ids='join_crm_with_telemetry', key='mart_data')

    if not mart_csv:
        raise ValueError("Нет данных для загрузки")

    reader = csv.DictReader(StringIO(mart_csv))
    rows = []

    for row in reader:
        processed_row = (
            int(row['user_id']),
            row['name'],
            int(float(row['age'])) if row['age'] else 0,
            row['gender'],
            row['email'],
            row['country'],
            int(row['total_signals']),
            float(row['avg_signal_duration_sec']),
            float(row['avg_signal_amplitude']),
            int(row['max_frequency']),
            parse_datetime(row['last_signal_time']),  
            row['muscle_usage_count']
        )
        rows.append(processed_row)

    if not rows:
        logging.info("Нет данных для вставки.")
        return

    clickhouse_hook = ClickHouseHook(clickhouse_conn_id='clickhouse_conn')
    clickhouse_hook.execute("INSERT INTO report_patient_activity_mart VALUES", rows)
    logging.info(f"Загружено {len(rows)} строк в ClickHouse")

load_task = PythonOperator(
    task_id='load_mart_to_clickhouse',
    python_callable=load_mart_data,
    dag=dag,
)

extract_users_task >> join_task
extract_telemetry_task >> join_task
join_task >> create_table_task >> load_task