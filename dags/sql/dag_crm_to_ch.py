from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow_clickhouse_plugin.operators.clickhouse import ClickHouseOperator
from airflow_clickhouse_plugin.hooks.clickhouse import ClickHouseHook
from datetime import datetime

def generate_crm_data():
    return [
        {
            "id": 1,
            "name": "user1",
            "email": "user1@example.com",
            "devices": ["1-device1", "1-device2"],
        },
        {
            "id": 2,
            "name": "user2",
            "email": "user2@example.com",
            "devices": ["2-device1", "2-device2"],
        },
    ]

def check_if_data_exists(**context):
    hook = ClickHouseHook(clickhouse_conn_id="clickhouse")
    result = hook.execute("SELECT count() FROM crm_customers_data")
    count = result[0][0] if result else 0

    print(f"Data exists ({count} rows).")
    
    if count > 0:
        print(f"Data exists ({count} rows). Skipping insertion.")
        return "skip_insertion"
    else:
        return "insert_crm_data_task"

def insert_data_python_func(**context):
    data = generate_crm_data()
    rows = []
    for item in data:
        rows.append((
            item['id'],
            item['name'],
            item['email'],
            item['devices']
        ))
    
    hook = ClickHouseHook(clickhouse_conn_id="clickhouse")
    hook.execute(
        "INSERT INTO crm_customers_data (id, name, email, devices) VALUES",
        rows
    )
    print(f"Successfully inserted {len(rows)} rows into crm_customers_data")

with DAG(
    dag_id="dag_crm_to_ch",
    start_date=datetime(2025, 1, 1),
    schedule_interval='* * * * *',
    catchup=False,
    is_paused_upon_creation=False,
) as dag:

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS crm_customers_data (
        id Int32,
        name String,
        email String,
        devices Array(String),
    ) ENGINE = MergeTree()
    ORDER BY id
    """
    
    create_table_task = ClickHouseOperator(
        task_id="create_table_task",
        sql=create_table_sql,
        clickhouse_conn_id="clickhouse",
    )

    branch_task = BranchPythonOperator(
        task_id="check_if_data_exists",
        python_callable=check_if_data_exists,
    )

    insert_crm_data_task = PythonOperator(
        task_id="insert_crm_data_task",
        python_callable=insert_data_python_func,
    )

    skip_insertion = EmptyOperator(
        task_id="skip_insertion"
    )

    create_table_task >> branch_task
    branch_task >> [insert_crm_data_task, skip_insertion]