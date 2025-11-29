from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime
from airflow_clickhouse_plugin.hooks.clickhouse import ClickHouseHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator

# Helper to calculate stats from raw telemetry
def calculate_aggregates(telemetry_rows):
    if not telemetry_rows:
        return 0, 0, 0, 0, 0, None
    
    # Assuming the value to aggregate is at index 2 of the telemetry row
    # You must adjust this index based on your actual ClickHouse 'telemetry' table structure
    # Example row: (email, TelemetryData, DateTime, DeviceId)
    values = [float(row[1]) for row in telemetry_rows if row[1] is not None] 
    
    if not values:
        return 0, 0, 0, 0, 0, None

    t_count = len(values)
    t_sum = sum(values)
    t_avg = t_sum / t_count
    t_min = min(values)
    t_max = max(values)
    # Assuming DateTime is at index 2
    last_time = telemetry_rows[-1][2] if len(telemetry_rows[-1]) > 2 else datetime.now()
    
    return t_count, t_sum, t_avg, t_min, t_max, last_time

def get_crm_customers_data():
    hook = ClickHouseHook(clickhouse_conn_id="clickhouse")
    # execute returns tuples. We can map them if we know the order.
    # Assuming schema: (customer_name, customer_email, devices array)
    rows = hook.execute("SELECT name, email, devices FROM crm_customers_data")
    
    # Convert tuples to dicts for safety
    customers = []
    for row in rows:
        customers.append({
            'name': row[0],
            'email': row[1],
            'devices': row[2] # ClickHouse Array matches Python list
        })
    return customers

def get_last_telemetry_time(email: str, device_id: str):
    hook = PostgresHook(postgres_conn_id="postgres")
    # Use parameters to prevent SQL injection
    sql = "SELECT last_telemetry_time FROM reports WHERE customer_email = %s AND device_id = %s ORDER BY last_telemetry_time DESC LIMIT 1"
    records = hook.get_records(sql, parameters=(email, device_id))
    
    if records and records[0]:
        return records[0][0]
    return None

def get_telemetry_data(email: str, device_id: str, start_time: datetime):
    hook = ClickHouseHook(clickhouse_conn_id="clickhouse")
    # Note: formatting datetime for ClickHouse usually requires string format
    start_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
    
    sql = f"SELECT Email, TelemetryData, DateTime, DeviceId FROM telemetry WHERE Email = '{email}' AND DeviceId = '{device_id}' AND DateTime >= '{start_str}'"
    return hook.execute(sql)

def insert_report_data(email: str, name: str, device_id: str, stats: tuple):
    t_count, t_sum, t_avg, t_min, t_max, last_time = stats
    
    if t_count == 0:
        print(f"No new data to insert for {email} - {device_id}")
        return

    hook = PostgresHook(postgres_conn_id="postgres")
    sql = """
        INSERT INTO reports 
        (customer_name, customer_email, device_id, telemetry_count, telemetry_sum, telemetry_avg, telemetry_min, telemetry_max, last_telemetry_time) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    hook.run(sql, parameters=(name, email, device_id, t_count, t_sum, t_avg, t_min, t_max, last_time))

def process_crm_customers_data():
    crm_customers_data = get_crm_customers_data()
    
    for customer in crm_customers_data:
        # Now accessing by key works because we converted to dict in get_crm_customers_data
        for device in customer['devices']:
            
            last_ts = get_last_telemetry_time(customer['email'], device)
            if not last_ts:
                last_ts = datetime(2025, 1, 1)
            
            # 1. Fetch Raw Data
            raw_telemetry = get_telemetry_data(customer['email'], device, last_ts)
            
            # 2. Transform (Calculate Aggregates)
            stats = calculate_aggregates(raw_telemetry)
            
            # 3. Load (Insert into Postgres)
            insert_report_data(customer['email'], customer['name'], device, stats)

with DAG(
    dag_id="dag_reports",
    schedule_interval='* * * * *',
    start_date=datetime(2025, 1, 1),
    catchup=False,
    is_paused_upon_creation=False,
) as dag:

    # Added explicit column names to match the insert logic
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS reports (    
        id SERIAL PRIMARY KEY,
        customer_name VARCHAR(255),
        customer_email VARCHAR(255) NOT NULL,
        device_id VARCHAR(255) NOT NULL,
        telemetry_sum DOUBLE PRECISION,
        telemetry_avg DOUBLE PRECISION,
        telemetry_min DOUBLE PRECISION,
        telemetry_max DOUBLE PRECISION,
        telemetry_count INTEGER,
        last_telemetry_time TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_reports_customer_email ON reports(customer_email);
    """

    create_table_task = PostgresOperator(
        task_id="create_table_task",
        sql=create_table_sql,
        postgres_conn_id="postgres",
    )

    process_crm_customers_data_task = PythonOperator(
        task_id="process_crm_customers_data_task",
        python_callable=process_crm_customers_data,
    )

    create_table_task >> process_crm_customers_data_task