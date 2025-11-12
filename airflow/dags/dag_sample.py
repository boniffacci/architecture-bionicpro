from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime
import csv

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2024, 12, 1),
}

def generate_crm():
    CSV_FILE_PATH = './dags/data/crm_sample.csv'
    with open( CSV_FILE_PATH, 'r') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=";")
    
        insert_queries = []
        is_header = True
        for row in csvreader:
            if is_header:
                is_header = False
                continue
            insert_query = f"INSERT INTO crm_table (id,user_id,user_name,email,prosthesis_model,prosthesis_serial,installation_date) VALUES ({row[0]}, '{row[1]}', '{row[2]}','{row[3]}','{row[4]}','{row[5]}','{row[6]}');"
            insert_queries.append(insert_query)
        
        with open('./dags/sql/insert_crm.sql', 'w') as f:
            for query in insert_queries:
                f.write(f"{query}\n")

def generate_telemetry():
    CSV_FILE_PATH = './dags/data/telemetry_sample.csv'
    with open( CSV_FILE_PATH, 'r') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=";")
    
        insert_queries = []
        is_header = True
        for row in csvreader:
            if is_header:
                is_header = False
                continue
            insert_query = f"INSERT INTO telemetry_table (id,user_id,usage_date,session_count,total_usage_minutes,max_force_application,avg_battery_level,error_codes,last_active) VALUES ({row[0]}, '{row[1]}', '{row[2]}',{row[3]},{row[4]},{row[5]},{row[6]},'{row[7]}','{row[8]}');"
            insert_queries.append(insert_query)
        
        with open('./dags/sql/insert_telemetry.sql', 'w') as f:
            for query in insert_queries:
                f.write(f"{query}\n")

with DAG('init_data',
         default_args=default_args,
         schedule_interval='@once',
         tags=['init', 'etl'],
         catchup=False) as dag:

    create_crm_table = PostgresOperator(
        task_id='create_crm_table',
        postgres_conn_id='write_to_pg',
        sql="""
        DROP TABLE IF EXISTS crm_table;
        CREATE TABLE crm_table (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL,
            user_name VARCHAR(100) NOT NULL,
            email VARCHAR(150) NOT NULL,
            prosthesis_model VARCHAR(100) NOT NULL,
            prosthesis_serial VARCHAR(50) NOT NULL UNIQUE,
            installation_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    create_telemetry_table = PostgresOperator(
        task_id='create_telemetry_table',
        postgres_conn_id='write_to_pg',
        sql="""
        DROP TABLE IF EXISTS telemetry_table;
        CREATE TABLE telemetry_table (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL,
            usage_date DATE NOT NULL,
            session_count INTEGER NOT NULL DEFAULT 0,
            total_usage_minutes INTEGER NOT NULL DEFAULT 0,
            max_force_application FLOAT NOT NULL DEFAULT 0,
            avg_battery_level FLOAT NOT NULL DEFAULT 0,
            error_codes JSONB DEFAULT '[]'::jsonb,
            last_active TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    generate_crm_queries = PythonOperator(
        task_id='generate_crm_queries',
        python_callable=generate_crm
    )

    generate_telemetry_queries = PythonOperator(
        task_id='generate_telemetry_queries',
        python_callable=generate_telemetry
    )

    run_insert_crm_queries = PostgresOperator(
        task_id='run_insert_crm_queries',
        postgres_conn_id='write_to_pg',
        sql='sql/insert_crm.sql'
    )

    run_insert_telemetry_queries = PostgresOperator(
        task_id='run_insert_telemetry_queries',
        postgres_conn_id='write_to_pg',
        sql='sql/insert_telemetry.sql'
    )

    create_crm_table>>create_telemetry_table>>generate_crm_queries>>generate_telemetry_queries>>run_insert_crm_queries>>run_insert_telemetry_queries