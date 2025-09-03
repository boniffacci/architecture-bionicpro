
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.hooks.base import BaseHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging

# pip install clickhouse-driver psycopg2-binary
try:
    from clickhouse_driver import Client as CHClient
except Exception as e:
    CHClient = None
    logging.warning("clickhouse-driver not available: %s", e)

CRM_CONN_ID = "crm_postgres"
CH_CONN_ID = "olap_clickhouse"

default_args = {
    "owner": "data-eng",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="reports",
    default_args=default_args,
    start_date=datetime(2025, 9, 1),
    schedule_interval="0 * * * *",
    catchup=False,
    tags=["bionicpro", "etl", "reports"],
) as dag:

    def _get_ch_client():
        conn = BaseHook.get_connection(CH_CONN_ID)
        extras = conn.extra_dejson or {}
        protocol = extras.get("protocol", "native")
        if protocol == "http":
            return CHClient(host=conn.host, port=conn.port or 8123, user=conn.login or "default",
                            password=conn.password or "", database=conn.schema or "default",
                            settings={"use_numpy": False}, secure=extras.get("secure", False))
        else:
            return CHClient(host=conn.host, port=conn.port or 9000, user=conn.login or "default",
                            password=conn.password or "", database=conn.schema or "default")

    def create_tables(**context):
        if CHClient is None:
            raise RuntimeError("clickhouse-driver is not installed")
        ch = _get_ch_client()
        # Provide schema alongside DAG in Airflow
        ddl = open("/opt/airflow/dags/clickhouse_schema.sql", "r").read()
        for stmt in [s.strip() for s in ddl.split(";") if s.strip()]:
            ch.execute(stmt)

    def extract_crm_to_stage(**context):
        if CHClient is None:
            raise RuntimeError("clickhouse-driver is not installed")
        pg = PostgresHook(postgres_conn_id=CRM_CONN_ID)
        rows = pg.get_records("SELECT id, name, email, COALESCE(age,0), COALESCE(gender,''), COALESCE(country,''), COALESCE(address,''), COALESCE(phone,'') FROM customers")
        logging.info("Fetched %d CRM rows", len(rows))

        ch = _get_ch_client()
        ch.execute("TRUNCATE TABLE IF EXISTS reports.crm_customers")
        if rows:
            ch.execute("INSERT INTO reports.crm_customers (id, name, email, age, gender, country, address, phone) VALUES", rows)

    def build_user_report_mart(**context):
        if CHClient is None:
            raise RuntimeError("clickhouse-driver is not installed")
        ch = _get_ch_client()
        delete_sql = "ALTER TABLE reports.user_report_mart DELETE WHERE day >= today() - 1;"
        insert_sql = """
        INSERT INTO reports.user_report_mart
        SELECT
            d.day, d.user_id,
            c.name, c.email, c.age, c.gender, c.country,
            d.prosthesis_type, d.muscle_group,
            d.signals, d.avg_amplitude, d.p95_amplitude,
            d.avg_frequency, d.avg_duration,
            d.first_signal, d.last_signal
        FROM reports.user_emg_daily AS d
        LEFT JOIN reports.crm_customers AS c ON d.user_id = c.id
        WHERE d.day >= today() - 1;
        """
        ch.execute(delete_sql)
        ch.execute(insert_sql)

    create_clickhouse = PythonOperator(task_id="create_clickhouse_tables", python_callable=create_tables)
    extract_crm = PythonOperator(task_id="extract_crm_to_stage", python_callable=extract_crm_to_stage)
    build_mart = PythonOperator(task_id="build_user_report_mart", python_callable=build_user_report_mart)

    create_clickhouse >> extract_crm >> build_mart
