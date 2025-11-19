from datetime import timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

import psycopg2
from clickhouse_driver import Client as ClickHouseClient


# ---------- Настройки подключений ----------
# В учебном окружении ты можешь оставить так
# или подставить реальные хосты/порты из docker-compose.
CRM_DSN = {
    "host": "crm-postgres",
    "dbname": "crm",
    "user": "crm_user",
    "password": "crm_password",
}

CLICKHOUSE_HOST = "clickhouse"
CLICKHOUSE_DB = "bionicpro"


# ---------- Шаг 1: Extract CRM ----------
def extract_crm(**context):
    """
    Забираем данные о пользователях и их протезах из CRM
    и складываем во временную CRM-таблицу в ClickHouse.
    """

    # 1. Читаем из CRM (PostgreSQL)
    conn = psycopg2.connect(**CRM_DSN)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            u.id        AS user_id,
            u.country   AS country,
            u.segment   AS segment,
            p.id        AS prosthesis_id,
            p.tariff    AS tariff
        FROM users u
        JOIN prostheses p ON p.user_id = u.id;
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # 2. Пишем во временную таблицу ClickHouse
    ch = ClickHouseClient(host=CLICKHOUSE_HOST, database=CLICKHOUSE_DB)

    ch.execute(
        """
        CREATE TABLE IF NOT EXISTS crm_users_tmp (
            user_id       UInt64,
            country       String,
            segment       String,
            prosthesis_id UInt64,
            tariff        String
        )
        ENGINE = Memory
        """
    )

    ch.execute("TRUNCATE TABLE crm_users_tmp")

    if rows:
        ch.execute(
            """
            INSERT INTO crm_users_tmp
            (user_id, country, segment, prosthesis_id, tariff)
            VALUES
            """,
            rows,
        )


# ---------- Шаг 2: Aggregate telemetry ----------
def aggregate_telemetry(**context):
    """
    Агрегируем сырую телеметрию по пользователю/протезу/дате.
    Результат кладём в таблицу telemetry_agg_daily.
    Ожидаем, что сырые данные лежат в telemetry_raw.
    """

    ch = ClickHouseClient(host=CLICKHOUSE_HOST, database=CLICKHOUSE_DB)

    # таблица с агрегатами (если нет — создаём)
    ch.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry_agg_daily (
            user_id           UInt64,
            prosthesis_id     UInt64,
            report_date       Date,
            total_active_sec  UInt32,
            avg_reaction_ms   Float32,
            movements_count   UInt32,
            errors_count      UInt32,
            battery_avg_pct   Float32,
            last_telemetry_ts DateTime
        )
        ENGINE = MergeTree
        PARTITION BY toYYYYMM(report_date)
        ORDER BY (user_id, prosthesis_id, report_date)
        """
    )

    # для учебного задания пересчитываем всё; в реале лучше делать инкремент
    ch.execute("TRUNCATE TABLE telemetry_agg_daily")

    ch.execute(
        """
        INSERT INTO telemetry_agg_daily
        SELECT
            user_id,
            prosthesis_id,
            toDate(ts)                         AS report_date,
            sum(active_seconds)                AS total_active_sec,
            avg(reaction_ms)                   AS avg_reaction_ms,
            count()                            AS movements_count,
            sumIf(1, has_error)                AS errors_count,
            avg(battery_level_pct)             AS battery_avg_pct,
            max(ts)                            AS last_telemetry_ts
        FROM telemetry_raw
        GROUP BY
            user_id,
            prosthesis_id,
            report_date
        """
    )


# ---------- Шаг 3: Build report mart ----------
def build_report_mart(**context):
    """
    Строим витрину report_user_prosthesis_daily
    как join агрегатов телеметрии и CRM-данных.
    """

    ch = ClickHouseClient(host=CLICKHOUSE_HOST, database=CLICKHOUSE_DB)

    # витрина (структура совпадает с SQL-файлом)
    ch.execute(
        """
        CREATE TABLE IF NOT EXISTS report_user_prosthesis_daily (
            user_id           UInt64,
            prosthesis_id     UInt64,
            report_date       Date,
            total_active_sec  UInt32,
            avg_reaction_ms   Float32,
            movements_count   UInt32,
            errors_count      UInt32,
            battery_avg_pct   Float32,
            last_telemetry_ts DateTime,
            crm_country       String,
            crm_segment       String,
            crm_tariff        String
        )
        ENGINE = MergeTree
        PARTITION BY toYYYYMM(report_date)
        ORDER BY (user_id, prosthesis_id, report_date)
        """
    )

    ch.execute("TRUNCATE TABLE report_user_prosthesis_daily")

    ch.execute(
        """
        INSERT INTO report_user_prosthesis_daily
        SELECT
            t.user_id,
            t.prosthesis_id,
            t.report_date,
            t.total_active_sec,
            t.avg_reaction_ms,
            t.movements_count,
            t.errors_count,
            t.battery_avg_pct,
            t.last_telemetry_ts,
            c.country   AS crm_country,
            c.segment   AS crm_segment,
            c.tariff    AS crm_tariff
        FROM telemetry_agg_daily AS t
        LEFT JOIN crm_users_tmp AS c
          ON c.user_id = t.user_id
         AND c.prosthesis_id = t.prosthesis_id
        """
    )


# ---------- Описание DAG ----------

default_args = {
    "owner": "bionicpro",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="bionicpro_reports_etl",
    default_args=default_args,
    description="ETL для витрины отчётов по работе протезов",
    schedule_interval="0 * * * *",  # каждый час; можно сменить на '@daily'
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["bionicpro", "reports"],
) as dag:

    t_extract_crm = PythonOperator(
        task_id="extract_crm",
        python_callable=extract_crm,
    )

    t_agg_telemetry = PythonOperator(
        task_id="aggregate_telemetry",
        python_callable=aggregate_telemetry,
    )

    t_build_mart = PythonOperator(
        task_id="build_report_mart",
        python_callable=build_report_mart,
    )

    [t_extract_crm, t_agg_telemetry] >> t_build_mart
