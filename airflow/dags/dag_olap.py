from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime, timedelta
import logging
import pandas as pd

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

def extract_data():
    try:
        pg_hook = PostgresHook(postgres_conn_id='write_to_pg')
        
        query = """
        SELECT 
            c.user_id,
            c.user_name,
            c.email,
            c.prosthesis_model,
            c.prosthesis_serial,
            c.installation_date,
            t.usage_date,
            COUNT(t.session_count) as total_sessions,
            SUM(t.total_usage_minutes) as total_usage_minutes,
            AVG(t.max_force_application) as avg_max_force,
            AVG(t.avg_battery_level) as avg_battery_level,
            COUNT(t.error_codes) as total_error_count,
            MAX(t.last_active) as last_active
        FROM crm_table c
        LEFT JOIN telemetry_table t ON c.user_id = t.user_id
        GROUP BY 
            c.user_id, c.user_name, c.email, c.prosthesis_model, 
            c.prosthesis_serial, c.installation_date, t.usage_date
        """
        
        connection = pg_hook.get_conn()
        cursor = connection.cursor()
        cursor.execute(query)
        
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return pd.DataFrame(results, columns=columns)
        
    except Exception as e:
        logging.error(f"Error extracting data: {str(e)}")
        raise

def transform_data(**kwargs):
    ti = kwargs['ti']
    df = ti.xcom_pull(task_ids='extract_data')
    
    if df.empty:
        logging.info("No data to transform")
        return pd.DataFrame()
    
    df['usage_date'] = pd.to_datetime(df['usage_date'])
    df['installation_date'] = pd.to_datetime(df['installation_date'])
    df['last_active'] = pd.to_datetime(df['last_active'])
    
    df.fillna({
        'total_sessions': 0,
        'total_usage_minutes': 0,
        'avg_max_force': 0,
        'avg_battery_level': 0,
        'total_error_count': 0
    }, inplace=True)
    
    return df

def load_to_olap(**kwargs):
    ti = kwargs['ti']
    df = ti.xcom_pull(task_ids='transform_data')
    
    if df.empty:
        logging.info("No data to load")
        return
    
    try:
        pg_hook = PostgresHook(postgres_conn_id='write_to_pg')
        connection = pg_hook.get_conn()
        cursor = connection.cursor()
        
        insert_sql = """
        INSERT INTO olap_table (
            user_id, user_name, email, prosthesis_model, prosthesis_serial,
            installation_date, usage_date, total_sessions, total_usage_minutes,
            avg_max_force, avg_battery_level, total_error_count, last_active
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        records = []
        for _, row in df.iterrows():
            record = (
                row['user_id'], row['user_name'], row['email'], 
                row['prosthesis_model'], row['prosthesis_serial'],
                row['installation_date'], row['usage_date'],
                row['total_sessions'], row['total_usage_minutes'],
                row['avg_max_force'], row['avg_battery_level'],
                row['total_error_count'], row['last_active']
            )
            records.append(record)
        
        cursor.executemany(insert_sql, records)
        connection.commit()
        
        logging.info(f"Successfully loaded {len(records)} records to OLAP table")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        logging.error(f"Error loading data to OLAP: {str(e)}")
        raise

with DAG('olap_pipeline',
         default_args=default_args,
         schedule_interval='*/5 * * * *',
         tags=['olap', 'prosthesis', 'etl'],
         catchup=False) as dag:

    create_olap_table = PostgresOperator(
        task_id='create_olap_table',
        postgres_conn_id='write_to_pg',
        sql="""
            DROP TABLE IF EXISTS olap_table;
            CREATE TABLE olap_table (
                id SERIAL PRIMARY KEY,
                user_id UUID NOT NULL,
                user_name VARCHAR(100) NOT NULL,
                email VARCHAR(150) NOT NULL,
                prosthesis_model VARCHAR(100) NOT NULL,
                prosthesis_serial VARCHAR(50) NOT NULL,
                installation_date DATE NOT NULL,
                usage_date DATE NOT NULL,
                total_sessions INTEGER NOT NULL DEFAULT 0,
                total_usage_minutes INTEGER NOT NULL DEFAULT 0,
                avg_max_force FLOAT NOT NULL DEFAULT 0,
                avg_battery_level FLOAT NOT NULL DEFAULT 0,
                total_error_count INTEGER NOT NULL DEFAULT 0,
                last_active TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
    )

    extract_task = PythonOperator(
        task_id='extract_data',
        python_callable=extract_data,
        dag=dag,
    )

    transform_task = PythonOperator(
        task_id='transform_data',
        python_callable=transform_data,
        dag=dag,
    )

    load_task = PythonOperator(
        task_id='load_to_olap',
        python_callable=load_to_olap,
        dag=dag,
    )

    create_olap_table>>extract_task >> transform_task >> load_task