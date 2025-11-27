from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow_clickhouse_plugin.hooks.clickhouse import ClickHouseHook
from datetime import datetime
from datetime import timedelta
import pandas as pd
import logging

# Аргументы по умолчанию: владелец процесса и время отсчета для задачи
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2024, 12, 1),
}

def extract_crm_data():
    postgres_hook = PostgresHook(postgres_conn_id='crm_db')

    query = """
    SELECT id, name, email, age,
           gender, country, address, phone
    FROM customers
    """

    df = postgres_hook.get_pandas_df(query)

    logging.info(f"Crm data: {len(df)} records")
    logging.info(f"Crm columns: {list(df.columns)}")

    return df.to_dict('records')

def extract_telemetry_data():
    clickhouse_hook = ClickHouseHook(clickhouse_conn_id='telemetry_db')

    query = """
    SELECT user_id, prosthesis_type, muscle_group, signal_frequency, 
           signal_duration, signal_amplitude, signal_time
    FROM emg_sensor_data
    """

    result = clickhouse_hook.execute(query, with_column_types=True)

    # Extract data and column names
    data = result[0]
    column_names = [col_info[0] for col_info in result[1]]

    # Create the Pandas DataFrame
    df = pd.DataFrame(data=data, columns=column_names)
    df['signal_time'] = df['signal_time'].dt.strftime('%Y-%m-%d %H:%M:%S%z')

    logging.info(f"Telemetry data: {len(data)} records")
    logging.info(f"Telemetry columns: {list(column_names)}")

    return df.to_dict('records')

def join_data(**kwargs):
    ti = kwargs['ti']

    crm_data = ti.xcom_pull(task_ids='extract_crm_data')
    telemetry_data = ti.xcom_pull(task_ids='extract_telemetry_data')

    df_crm = pd.DataFrame(crm_data).rename(columns={'id': 'user_id','name': 'user_name', 'email': 'user_email', 'age': 'user_age', 'gender': 'user_gender', 'country': 'user_country', 'address': 'user_address', 'phone': 'user_phone'})
    df_telemetry = pd.DataFrame(telemetry_data)

    df_merge = pd.merge(
        df_crm,
        df_telemetry,
        on='user_id',
        how='inner'
    )

    logging.info(f"Merged data: {len(df_merge)} records")
    logging.info(f"Merged columns: {list(df_merge.columns)}")

    return df_merge.to_dict('records')

def save_to_olap(**kwargs):
    ti = kwargs['ti']
    data = ti.xcom_pull(task_ids='join_data')

    if not data:
        logging.warning("No input data")
        return

    df_merge = pd.DataFrame(data)
    df_merge['signal_time'] = pd.to_datetime(df_merge['signal_time'])

    logging.info(df_merge)

    clickhouse_hook = ClickHouseHook(clickhouse_conn_id='olap_db')

    columns = ', '.join(df_merge.columns)

    insert_query = f"INSERT INTO report ({columns}) VALUES"

    try:
        clickhouse_hook.execute(insert_query, df_merge.values.tolist())
        logging.info(f"Records saved to 'report' table: {len(df_merge)}")
    except Exception as e:
        logging.error(f"Error during save to 'report': {str(e)}")
        raise

# Определяем DAG
with DAG('report_dag',
         default_args=default_args, #аргументы по умолчанию в начале скрипта
         schedule_interval = timedelta(minutes=5), #запускаем каждые 5 минут
         catchup=False #предотвращает повторное выполнение DAG для пропущенных расписаний.
) as dag:

    extract_crm_task = PythonOperator(
        task_id='extract_crm_data',
        python_callable=extract_crm_data,
        provide_context=True,
    )

    extract_telemetry_task = PythonOperator(
        task_id='extract_telemetry_data',
        python_callable=extract_telemetry_data,
        provide_context=True,
    )

    join_task = PythonOperator(
        task_id='join_data',
        python_callable=join_data,
        provide_context=True,
    )

    save_olap_task = PythonOperator(
        task_id='save_to_olap',
        python_callable=save_to_olap,
        provide_context=True,
    )

    [extract_crm_task, extract_telemetry_task] >> join_task >> save_olap_task