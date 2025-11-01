# dags/reports_etl.py
from time import strftime
from datetime import datetime, timedelta

import pandas as pd
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow_clickhouse_plugin.hooks.clickhouse import ClickHouseHook
from airflow import DAG
from airflow.operators.python import PythonOperator

dag = DAG(
    dag_id="reports_etl",
    start_date=datetime(2025, 10, 18),
    schedule_interval="0 1 * * *",
)


def extract_crm(**context):
    pg = PostgresHook(postgres_conn_id="crm_db")
    sql = "SELECT id as user_id, email, name, country, prosthesis_id FROM crm"
    df = pg.get_pandas_df(sql)
    df.to_parquet("/tmp/crm.parquet", index=False)
    return True


def extract_telemetry(**context):
    execution_date = str(context["execution_date"])
    date = execution_date.split(" ")[0]

    pg = PostgresHook(postgres_conn_id="telemetry_db")
    sql = """
        SELECT user_id, prosthesis_id, ts, metric_type, metric_value
        FROM telemetry
        WHERE ts::date = %s
    """
    df = pg.get_pandas_df(sql, parameters=(date,))
    df.to_parquet("/tmp/telemetry.parquet", index=False)
    return True


def transform(**context):
    crm = pd.read_parquet("/tmp/crm.parquet")
    telemetry = pd.read_parquet("/tmp/telemetry.parquet")

    telemetry["prosthesis_id"] = telemetry["prosthesis_id"].astype(str)
    crm["prosthesis_id"] = crm["prosthesis_id"].astype(str)

    agg = (
        telemetry.groupby(["user_id", "prosthesis_id", "metric_type"])
        .agg(
            events_count=("ts", "count"),
            avg_metric=("metric_value", "mean"),
            min_metric=("metric_value", "min"),
            max_metric=("metric_value", "max"),
        )
        .reset_index()
    )

    rep = agg.merge(
        crm[["user_id", "name", "country", "prosthesis_id"]],
        on=["user_id", "prosthesis_id"],
        how="left",
    )

    rep.to_parquet("/tmp/report.parquet", index=False)
    return True


def save_to_clickhouse(**context):
    execution_date = str(context["execution_date"])
    date = execution_date.split(" ")[0]
    date = datetime.strptime(date, "%Y-%m-%d").date()
    report = pd.read_parquet("/tmp/report.parquet")
    records = report.to_dict(orient="records")

    ch = ClickHouseHook(clickhouse_conn_id="clickhouse_db")
    ch.execute("""
    CREATE TABLE IF NOT EXISTS reports_user_daily (
      date Date,
      user_id UInt64,
      prosthesis_id String,
      country String,
      events_count UInt32,
      metric_type String,
      avg_metric Float32,
      min_metric Float32,
      max_metric Float32

    ) ENGINE = MergeTree()
    PARTITION BY toYYYYMM(date)
    ORDER BY (user_id, date)
    """)

    rows = [
        (
            date,
            r.get("user_id"),
            str(r.get("prosthesis_id")) or "",
            str(r.get("metric_type")),
            r.get("country") or "",
            int(r.get("events_count") or 0),
            float(r.get("avg_metric") or 0),
            float(r.get("min_metric") or 0),
            float(r.get("max_metric") or 0),
        )
        for r in records
    ]

    if rows:
        ch.execute(
            "INSERT INTO reports_user_daily (date, user_id, prosthesis_id, metric_type, country, events_count, avg_metric, min_metric, max_metric) VALUES",
            rows,
        )
    return True


extract_crm_task = PythonOperator(
    task_id="extract_crm", python_callable=extract_crm, dag=dag
)

extract_telemetry_task = PythonOperator(
    task_id="extract_telemetry", python_callable=extract_telemetry, dag=dag
)

transform_task = PythonOperator(task_id="transform", python_callable=transform, dag=dag)

save_task = PythonOperator(task_id="save", python_callable=save_to_clickhouse, dag=dag)

[extract_crm_task, extract_telemetry_task] >> transform_task >> save_task
