from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.hooks.postgres_hook import PostgresHook
from airflow_clickhouse_plugin.operators.clickhouse import ClickHouseOperator
from airflow_clickhouse_plugin.hooks.clickhouse import ClickHouseHook
from datetime import datetime
import pandas as pd

# Аргументы по умолчанию: владелец процесса и время отсчёта для задачи
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2024, 12, 1),
    # 'schedule_interval': timedelta(seconds=60)
}

def extract_customers_from_crm_db():
    crm_db = PostgresHook(postgres_conn_id='airflow_crm_postgres')
    crm_db_conn = crm_db.get_conn()
    crm_db_cursor = crm_db_conn.cursor()
    crm_db_cursor.execute("SELECT id, name, email, age, gender, country, address, phone FROM customers")
    records = crm_db_cursor.fetchall()
    
    customers_columns = ['user_id', 'name', 'email', 'age', 'gender', 'country', 'address', 'phone']
    
    return pd.DataFrame(records, columns=customers_columns)


def extract_sensor_data_from_olap():
    olap_db_hook = ClickHouseHook(clickhouse_conn_id='airflow_olap_clickhouse')
    records = olap_db_hook.execute('SELECT user_id, prosthesis_type, muscle_group, signal_frequency, signal_duration, signal_amplitude, signal_time FROM emg_sensor_data')
    
    telemetry_columns = ['user_id', 'prosthesis_type', 'muscle_group', 'signal_frequency', 
          'signal_duration', 'signal_amplitude', 'signal_time']
    
    return pd.DataFrame(records, columns=telemetry_columns)

def transform_and_load(**kwargs):
    ti = kwargs['ti']
    
    telemetry_df = ti.xcom_pull(task_ids='extract_sensor_data_from_olap')
    customers_df = ti.xcom_pull(task_ids='extract_customers_from_crm_db')
        
    telemetry_agg = telemetry_df.groupby(['user_id', 'prosthesis_type', 'muscle_group']).agg({
        
        'signal_time': [
            ('total_signal_records', 'count'),
            ('active_days_count', lambda x: x.dt.date.nunique()),
            ('last_activity_date', 'max'),
            ('first_activity_date', 'min')
        ],
        
        'signal_amplitude': [
            ('avg_signal_amplitude', 'mean'),
            ('max_signal_amplitude', 'max'),
            ('signal_volatility', 'std'),
            ('signal_stability_index', lambda x: float(x.mean()) / float(x.max()) if float(x.max()) > 0 else 0.0)
        ],
        
        'signal_duration': [
            ('total_signal_duration_sec', 'sum'),
            ('avg_signal_duration', 'mean')
        ],
        
        'signal_frequency': [
            ('avg_signal_frequency', 'mean')
        ]
    }).round(3)
    
    telemetry_agg.columns = [f"{col[1]}" for col in telemetry_agg.columns]
    telemetry_agg = telemetry_agg.reset_index()
    
    telemetry_agg['days_since_last_training'] = (
        datetime.now() - telemetry_agg['last_activity_date']
    ).dt.days
    
    # Объединяем с CRM данными
    final_df = pd.merge(
        customers_df, 
        telemetry_agg, 
        on='user_id', 
        how='right'
    ).fillna(0)
    
    final_list = list(final_df.itertuples(index=False))
    
    sql="""
        INSERT INTO usage_reports (
            user_id,
            name,
            email,
            age,
            gender,
            country,
            address,
            phone ,
            prosthesis_type,
            muscle_group,
            total_signal_records,
            active_days_count,
            last_activity_date,
            first_activity_date,
            avg_signal_amplitude,
            max_signal_amplitude,
            signal_volatility,
            signal_stability_index,
            total_signal_duration_sec,
            avg_signal_duration,
            avg_signal_frequency,
            days_since_last_training
            ) VALUES
        """
    
    olap_db_hook = ClickHouseHook(clickhouse_conn_id='airflow_olap_clickhouse')
    olap_db_hook.execute(sql, final_list)
    

with DAG('crm_db_olap_dag',
         default_args=default_args, 
         schedule_interval='@once', 
         catchup=False) as dag: 
    
    # Создаём витрину в ClickHouse
    create_table = ClickHouseOperator(
        task_id='create_table',
        database='default',
        clickhouse_conn_id='airflow_olap_clickhouse',
        sql="""
        CREATE TABLE IF NOT EXISTS usage_reports (
            user_id UInt32,
            name String,
            email String,
            age Float64,
            gender String,
            country String,
            address String,
            phone String,
            prosthesis_type String,
            muscle_group String,
            total_signal_records Float64,
            active_days_count Float64,
            last_activity_date DateTime,
            first_activity_date DateTime,
            avg_signal_amplitude Float64,
            max_signal_amplitude Float64,
            signal_volatility Float64,
            signal_stability_index Float64,
            total_signal_duration_sec Float64,
            avg_signal_duration Float64,
            avg_signal_frequency Float64,
            days_since_last_training UInt32
        ) ENGINE = MergeTree()
        ORDER BY (user_id, prosthesis_type);
        """
    )
        
    task_get_customers_data = PythonOperator(
        task_id='extract_customers_from_crm_db',
        python_callable=extract_customers_from_crm_db,
        do_xcom_push=True
    )
    
    task_get_telemetry_data = PythonOperator(
        task_id='extract_sensor_data_from_olap',
        python_callable=extract_sensor_data_from_olap,
        do_xcom_push=True
    )
    
    task_transform_and_load= PythonOperator(
        task_id='transform_and_join_data',
        python_callable=transform_and_load

    )
        
    create_table>>task_get_customers_data>>task_get_telemetry_data>>task_transform_and_load