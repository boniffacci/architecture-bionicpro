from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator

ETL_JAR_PATH = "/opt/etl/etl-java.jar"
ETL_IMAGE = "bionicpro/etl-java:latest"

default_args = {
    'owner': 'bionicpro',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'bionicpro_reports_etl',
    default_args=default_args,
    description='ETL pipeline для витрины отчётов BionicPRO',
    schedule_interval='0 */1 * * *',
    catchup=False,
    max_active_runs=1,
    tags=['bionicpro', 'etl', 'reports'],
)

extract_crm = DockerOperator(
    task_id='extract_crm_java',
    image=ETL_IMAGE,
    api_version='auto',
    auto_remove=True,
    command='java -jar /app/etl-java.jar --job=extractCrmJob --date={{ ds }}',
    docker_url='unix://var/run/docker.sock',
    network_mode='bridge',
    environment={
        'CRM_API_URL': '{{ var.value.crm_api_url }}',
        'CLICKHOUSE_HOST': '{{ var.value.clickhouse_host }}',
        'CLICKHOUSE_PORT': '{{ var.value.clickhouse_port }}',
    },
    dag=dag,
)

extract_telemetry = DockerOperator(
    task_id='extract_telemetry_java',
    image=ETL_IMAGE,
    api_version='auto',
    auto_remove=True,
    command='java -jar /app/etl-java.jar --job=extractTelemetryJob --date={{ ds }}',
    docker_url='unix://var/run/docker.sock',
    network_mode='bridge',
    environment={
        'CORE_DB_HOST': '{{ var.value.core_db_host }}',
        'CORE_DB_PORT': '{{ var.value.core_db_port }}',
        'CLICKHOUSE_HOST': '{{ var.value.clickhouse_host }}',
        'CLICKHOUSE_PORT': '{{ var.value.clickhouse_port }}',
    },
    dag=dag,
)

build_mart = DockerOperator(
    task_id='build_mart_java',
    image=ETL_IMAGE,
    api_version='auto',
    auto_remove=True,
    command='java -jar /app/etl-java.jar --job=buildMartJob --date={{ ds }}',
    docker_url='unix://var/run/docker.sock',
    network_mode='bridge',
    environment={
        'CLICKHOUSE_HOST': '{{ var.value.clickhouse_host }}',
        'CLICKHOUSE_PORT': '{{ var.value.clickhouse_port }}',
    },
    dag=dag,
)

optimize_clickhouse = BashOperator(
    task_id='optimize_clickhouse',
    bash_command="""
    clickhouse-client --host {{ var.value.clickhouse_host }} \
                      --port {{ var.value.clickhouse_port }} \
                      --query "OPTIMIZE TABLE mart_report_user_daily FINAL"
    """,
    dag=dag,
)

extract_crm >> build_mart
extract_telemetry >> build_mart
build_mart >> optimize_clickhouse



