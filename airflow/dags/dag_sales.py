import csv
from datetime import datetime

from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator

from airflow import DAG

default_args = {
    "owner": "airflow",
    "start_date": datetime(2024, 12, 1),
}


def generate_insert_sales_queries():
    CSV_FILE_PATH = "sample_files/sample_sales.csv"
    with open(CSV_FILE_PATH, "r") as csvfile:
        csvreader = csv.reader(csvfile)

        insert_queries = []
        is_header = True
        for row in csvreader:
            if is_header:
                is_header = False
                continue
            insert_query = f"INSERT INTO sample_sales (id,order_number,total,discount,buyer_id) VALUES ({row[0]}, {row[1]}, {row[2]},{row[3]},{row[4]});"
            insert_queries.append(insert_query)

        with open("./dags/sql/insert_sales_queries.sql", "w") as f:
            for query in insert_queries:
                f.write(f"{query}\n")


def generate_insert_telemetry_queries():
    CSV_FILE_PATH = "sample_files/sample_telemetry.csv"
    with open(CSV_FILE_PATH, "r") as csvfile:
        csvreader = csv.reader(csvfile)

        insert_queries = []
        is_header = True
        for row in csvreader:
            if is_header:
                is_header = False
                continue
            insert_query = f"INSERT INTO sample_telemetry (id,buyer_id,sensor_type,timestamp,value) VALUES ({row[0]}, {row[1]}, {row[2]},{row[3]},{row[4]});"
            insert_queries.append(insert_query)

        with open("./dags/sql/insert_telemetry_queries.sql", "w") as f:
            for query in insert_queries:
                f.write(f"{query}\n")


# Определяем DAG
with DAG(
    "csv_to_postgres_dag",
    default_args=default_args,
    schedule_interval="@once",
    catchup=False,
) as dag:
    create_sales_table = PostgresOperator(
        task_id="create_sales_table",
        postgres_conn_id="write_to_postgres",
        sql="""
        DROP TABLE IF EXISTS sample_sales;
        CREATE TABLE sample_sales (
            id SERIAL PRIMARY KEY,
            order_number BIGINT,
            total NUMERIC(18,2),
            discount NUMERIC(18,2),
            buyer_id BIGINT
        );
        """,
    )
    create_telemetry_table = PostgresOperator(
        task_id="create_telemetry_table",
        postgres_conn_id="write_to_postgres",
        sql="""
        DROP TABLE IF EXISTS sample_telemetry;
        CREATE TABLE sample_telemetry (
            id SERIAL PRIMARY KEY,
            buyer_id BIGINT,
            sensor_type BIGINT,
            timestamp BIGINT,
            value BIGINT
        );
        """,
    )
    create_facade_table = PostgresOperator(
        task_id="create_facade_table",
        postgres_conn_id="write_to_postgres",
        sql="""
        DROP TABLE IF EXISTS sample_facade;
        CREATE TABLE sample_facade (
            id SERIAL PRIMARY KEY,
            buyer_id BIGINT,
            telemetry_count BIGINT,
            sales_amount NUMERIC(18,2)
        );
        """,
    )

    generate_sales_queries = PythonOperator(
        task_id="generate_insert_sales_queries",
        python_callable=generate_insert_sales_queries,
    )
    generate_telemetry_queries = PythonOperator(
        task_id="generate_insert_telemetry_queries",
        python_callable=generate_insert_telemetry_queries,
    )

    run_insert_sales_queries = PostgresOperator(
        task_id="run_insert_sales_queries",
        postgres_conn_id="write_to_postgres",
        sql="sql/insert_sales_queries.sql",
    )
    run_insert_telemetry_queries = PostgresOperator(
        task_id="run_insert_telemetry_queries",
        postgres_conn_id="write_to_postgres",
        sql="sql/insert_telemetry_queries.sql",
    )
    run_insert_facade_query = PostgresOperator(
        task_id="run_insert_facade_query",
        postgres_conn_id="write_to_postgres",
        sql="sql/insert_facade_query.sql",
    )

    result = (
        create_sales_table
        >> create_telemetry_table
        >> create_facade_table
        >> generate_sales_queries
        >> generate_telemetry_queries
        >> run_insert_sales_queries
        >> run_insert_telemetry_queries
        >> run_insert_facade_query
    )
