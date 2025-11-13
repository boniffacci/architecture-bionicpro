"""
BionicPRO Reports ETL DAG

Оркестрирует ETL процесс для создания витрины отчётов:
1. Извлечение данных из CRM (Java job)
2. Извлечение телеметрии из Core DB (Java job)
3. Агрегация и загрузка в ClickHouse mart (Java job)
4. Оптимизация ClickHouse таблиц

Расписание: каждый час
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator

# Путь к JAR файлу ETL (монтируется в контейнер)
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
    schedule_interval='0 */1 * * *',  # Каждый час
    catchup=False,
    max_active_runs=1,
    tags=['bionicpro', 'etl', 'reports'],
)

# Task 1: Извлечение данных CRM (Java job)
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

# Task 2: Извлечение телеметрии (Java job)
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

# Task 3: Построение витрины (Java job - агрегация)
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

# Task 4: Оптимизация ClickHouse (можно через BashOperator с clickhouse-client)
optimize_clickhouse = BashOperator(
    task_id='optimize_clickhouse',
    bash_command="""
    clickhouse-client --host {{ var.value.clickhouse_host }} \
                      --port {{ var.value.clickhouse_port }} \
                      --query "OPTIMIZE TABLE mart_report_user_daily FINAL"
    """,
    dag=dag,
)

# Task Dependencies
extract_crm >> build_mart
extract_telemetry >> build_mart
build_mart >> optimize_clickhouse



