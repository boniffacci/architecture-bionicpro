from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from clickhouse_driver import Client

def extract_customers_fn():
    pg_hook = PostgresHook(postgres_conn_id="crm_db")
    sql = "SELECT id, name, email, country FROM customers;"
    return pg_hook.get_records(sql)

def aggregate_emg_data_fn():
    client = Client(host="olap_db", port=9000)
    sql = """
        SELECT user_id, prosthesis_type, muscle_group,
               COUNT(*) as total_signals,
               AVG(signal_frequency) as avg_frequency,
               AVG(signal_duration) as avg_duration,
               AVG(signal_amplitude) as avg_amplitude,
               MAX(signal_time) as last_signal_time
        FROM emg_sensor_data
        GROUP BY user_id, prosthesis_type, muscle_group
    """
    return client.execute(sql)

def build_mart_fn(**kwargs):
    ti = kwargs["ti"]
    customers = ti.xcom_pull(task_ids="extract_customers")
    emg_data = ti.xcom_pull(task_ids="aggregate_emg")

    customer_map = {row[0]: row[1:] for row in customers}
    merged = []
    for (user_id, prosthesis_type, muscle_group,
         total_signals, avg_frequency, avg_duration,
         avg_amplitude, last_signal_time) in emg_data:

        if user_id in customer_map:
            name, email, country = customer_map[user_id]
            merged.append((user_id, name, email, country,
                           prosthesis_type, muscle_group,
                           total_signals, avg_frequency,
                           avg_duration, avg_amplitude,
                           last_signal_time))

    client = Client(host="olap_db", port=9000)
    client.execute("INSERT INTO customer_emg_analytics VALUES", merged)

with DAG(
    dag_id="crm_emg_mart",
    start_date=datetime(2025, 11, 18),
    schedule_interval="*/5 * * * *",
    catchup=False,
) as dag:

    extract_customers = PythonOperator(
        task_id="extract_customers",
        python_callable=extract_customers_fn,
    )

    aggregate_emg = PythonOperator(
        task_id="aggregate_emg",
        python_callable=aggregate_emg_data_fn,
    )

    build_mart = PythonOperator(
        task_id="build_mart",
        python_callable=build_mart_fn,
    )

    [extract_customers, aggregate_emg] >> build_mart