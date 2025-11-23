from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow_clickhouse_plugin.hooks.clickhouse import ClickHouseHook
from datetime import datetime
import pandas as pd
import logging

# Аргументы по умолчанию: владелец процесса и время отсчета для задачи
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2024, 12, 1),
}

def extract_crm_data():
    #try:
        postgres_hook = PostgresHook(postgres_conn_id='crm_db')

        query = """
        SELECT id, name, email, age,
               gender, country, address, phone
        FROM customers
        """

        df = postgres_hook.get_pandas_df(query)

        logging.info(f"Crm data: {len(df)} records")
        logging.info(f"Crm columns: {list(df.columns)}")

        return df
    #except Exception as e:
    #    logging.info(f"Crm error: {e}")
    #    return pd.DataFrame()

def extract_telemetry_data():
    #try:
        clickhouse_hook = ClickHouseHook(clickhouse_conn_id='telemetry_db')

        query = """
        SELECT user_id, prosthesis_type, muscle_group, signal_frequency, 
               signal_duration, signal_amplitude, signal_time
        FROM emg_sensor_data
        """

        records = clickhouse_hook.execute(query)

        logging.info(f"Telemetry data: {len(records)} records")

        if records:
            df = pd.DataFrame(data=result[0], columns=[c for c, _ in result[1]])
            logging.info(f"Telemetry columns: {list(df.columns)}")
            return df
        else:
            return pd.DataFrame()
    #except Exception as e:
    #    logging.info(f"Telemetry error: {e}")
    #    return pd.DataFrame()

def join_data(**kwargs): # kwargs???
    ti = kwargs['ti']

    crm_data = ti.xcom_pull(task_ids='extract_crm_data')
    telemetry_data = ti.xcom_pull(task_ids='extract_telemetry_data')

    df_crm = pd.DataFrame(crm_data)
    df_telemetry = pd.DataFrame(telemetry_data)

    merged_df = pd.merge(
        df_crm,
        df_telemetry,
        left_on='id',
        right_on='user_id',
        how='inner'
    )

    logging.info(f"Merged data: {len(merged_df)} records")
    logging.info(f"Merged columns: {list(merged_df.columns)}")

    result_data = merged_df.to_dict('records') # to_dict???
    return result_data

def save_to_olap(**kwargs):
    ti = kwargs['ti']
    transformed_data = ti.xcom_pull(task_ids='transform_and_join_data')

    if not transformed_data:
        logging.warning("Нет данных для загрузки")
        return

    clickhouse_hook = ClickHouseHook(clickhouse_conn_id='olap_db')

    insert_query = """
                   INSERT INTO report (user_name,
                                       user_email,
                                       user_phone,
                                       user_address,
                                       device_id,
                                       device_name,
                                       metric_value,
                                       metric_unit,
                                       metric_timestamp)
                   VALUES \
                   """

    try:
        clickhouse_hook.execute(insert_query, transformed_data)
        logging.info(f"Успешно загружено {len(transformed_data)} записей в таблицу report")
    except Exception as e:
        logging.error(f"Ошибка при загрузке данных отчёта: {str(e)}")
        raise

# Определяем DAG
with DAG('report_dag',
         default_args=default_args, #аргументы по умолчанию в начале скрипта
         schedule_interval = '@once', #timedelta(minutes=5), #запускаем каждые 5 минут
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

    [extract_crm_task, extract_telemetry_task] >> join_task #>> save_olap_task